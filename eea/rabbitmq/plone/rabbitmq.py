""" Configuration and utilities for RabbitMQ client
"""

from contextlib import contextmanager
from eea.rabbitmq.client.rabbitmq import RabbitMQConnector
from plone import api
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.registry.interfaces import IRegistry
from plone.z3cform import layout
from z3c.form import form
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.interface import Interface
from zope.schema import TextLine, Int
import logging
import transaction

logger = logging.getLogger("eea.rabbitmq.plone")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - "
    "%(name)s/%(filename)s/%(funcName)s - "
    "%(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class IRabbitMQClientSettings(Interface):
    """ Client settings for RabbitMQ
    """

    server = TextLine(title=u"Server Address",
                      required=True, default=u"localhost")
    port = Int(title=u"Server port", required=True, default=5672)
    username = TextLine(title=u"Username", required=True)
    password = TextLine(title=u"Password", required=True)


class RabbitMQClientControlPanelForm(RegistryEditForm):
    form.extends(RegistryEditForm)
    schema = IRabbitMQClientSettings


RabbitMQClientControlPanelView = layout.wrap_form(
    RabbitMQClientControlPanelForm, ControlPanelFormWrapper)
RabbitMQClientControlPanelView.label = u"RabbitMQ Client settings"


def get_rabbitmq_client_settings():
    """ Return the settings as set in site/@@rabbitmq-client-controlpanel

        Usage: s.server, s.port, s.username, s.password
    """
    registry = getUtility(IRegistry, context=api.portal.get())
    s = registry.forInterface(IRabbitMQClientSettings)
    return s


@contextmanager
def get_rabbitmq_conn(queue, context=None):
    """ Context manager to connect to RabbitMQ
    """

    if context is None:
        context = getSite()

    s = get_rabbitmq_client_settings()

    rb = RabbitMQConnector(s.server, s.port, s.username, s.password)
    rb.open_connection()
    rb.declare_queue(queue)

    yield rb

    rb.close_connection()


def consume_messages(consumer, queue=None, context=None):
    """ Executes the callback on all messages existing in the queue
    """

    with get_rabbitmq_conn(queue, context) as conn:
        while not conn.is_queue_empty(queue):
            msg = conn.get_message(queue)
            consumer(msg)
            conn.get_channel().basic_ack(msg[0].delivery_tag)


class MessagesDataManager(object):
    """ Transaction aware data manager for RabbitMQ connections
    """

    def __init__(self):
        self.sp = 0
        self.messages = []
        self.txn = None

    def tpc_begin(self, txn):
        self.txn = txn

    def tpc_finish(self, txn):
        self.messages = []

    def tpc_vote(self, txn):
        # TODO: vote by trying to connect to rabbitmq server
        pass

    def tpc_abort(self, txn):
        self._checkTransaction(txn)

        if self.txn is not None:
            self.txn = None

        self.messages = []

    def abort(self, txn):
        self.messages = []

    def commit(self, txn):
        self._checkTransaction(txn)

        for queue, msg in self.messages:
            try:
                send_message(queue, msg)
            except Exception:
                logger.exception("RabbitMQ Connection exception")

        self.txn = None
        self.messages = []

    def savepoint(self):
        self.sp += 1
        return Savepoint(self)

    def sortKey(self):
        return self.__class__.__name__

    def add(self, queue, msg):
        logger.info("Add msg to queue: %s => %s", msg, queue)
        self.messages.append((queue, msg))

    def _checkTransaction(self, txn):
        if (txn is not self.txn and self.txn is not None):
            raise TypeError("Transaction missmatch", txn, self.txn)


class Savepoint(object):
    """ Savepoint implementation to allow rollback of queued messages
    """

    def __init__(self, dm):
        self.dm = dm
        self.sp = dm.sp
        self.messages = dm.messages[:]
        self.transaction = dm.transaction

    def rollback(self):
        if self.transaction is not self.dm.transaction:
            raise TypeError("Attempt to rollback stale rollback")
        if self.dm.sp < self.sp:
            raise TypeError("Attempt to roll back to invalid save point",
                            self.sp, self.dm.sp)
        self.dm.sp = self.sp
        self.dm.messages = self.messages[:]


def send_message(msg, queue, context=None):
    with get_rabbitmq_conn(queue=queue, context=context) as conn:
        conn.send_message(queue, msg)


def queue_msg(msg, queue=None):
    """ Queues a rabbitmq message in the given queue
    """

    _mdm = MessagesDataManager()
    transaction.get().join(_mdm)
    _mdm.add(queue, msg)
