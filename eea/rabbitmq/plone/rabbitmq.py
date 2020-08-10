""" Configuration and utilities for RabbitMQ client
"""
import os
from contextlib import contextmanager
import logging
import six
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
import transaction
from eea.rabbitmq.client.rabbitmq import RabbitMQConnector

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

RABBITMQ_HOST = six.text_type(os.environ.get("RABBITMQ_HOST", "") or
                              "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "") or "5672")
RABBITMQ_USER = six.text_type(os.environ.get("RABBITMQ_USER", ""))
RABBITMQ_PASS = six.text_type(os.environ.get("RABBITMQ_PASS", ""))


class IRabbitMQClientSettings(Interface):
    """ Client settings for RabbitMQ
    """

    server = TextLine(title=u"Server Address", required=True,
                      default=RABBITMQ_HOST)
    port = Int(title=u"Server port", required=True, default=RABBITMQ_PORT)
    username = TextLine(title=u"Username", required=True,
                        default=RABBITMQ_USER)
    password = TextLine(title=u"Password", required=True,
                        default=RABBITMQ_PASS)


class RabbitMQClientControlPanelForm(RegistryEditForm):
    """RabbitMQClientControlPanelForm."""

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

    @property
    def transaction(self):
        """transaction."""
        return self.txn

    @transaction.setter
    def transaction(self, value):
        """transaction.

        :param value:
        """
        self.txn = value

    def tpc_begin(self, txn):
        """tpc_begin.

        :param txn:
        """
        self.txn = txn

    def tpc_finish(self, txn):
        """tpc_finish.

        :param txn:
        """
        self.messages = []

    def tpc_vote(self, txn):
        """tpc_vote.

        :param txn:
        """
        # TO DO: vote by trying to connect to rabbitmq server
        pass

    def tpc_abort(self, txn):
        """tpc_abort.

        :param txn:
        """
        self._checkTransaction(txn)

        if self.txn is not None:
            self.txn = None

        self.messages = []

    def abort(self, txn):
        """abort.

        :param txn:
        """
        self.messages = []

    def commit(self, txn):
        """commit.

        :param txn:
        """
        self._checkTransaction(txn)

        for queue, msg in self.messages:
            try:
                send_message(msg, queue=queue)
            except Exception:
                logger.exception("RabbitMQ Connection exception")

        self.txn = None
        self.messages = []

    def savepoint(self):
        """savepoint."""
        self.sp += 1
        return Savepoint(self)

    def sortKey(self):
        """sortKey."""
        return self.__class__.__name__

    def add(self, queue, msg):
        """add.

        :param queue:
        :param msg:
        """
        logger.info("Add msg to queue: %s => %s", msg, queue)
        self.messages.append((queue, msg))

    def _checkTransaction(self, txn):
        """_checkTransaction.

        :param txn:
        """
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
        """rollback."""
        if self.transaction is not self.dm.transaction:
            raise TypeError("Attempt to rollback stale rollback")
        if self.dm.sp < self.sp:
            raise TypeError("Attempt to roll back to invalid save point",
                            self.sp, self.dm.sp)
        self.dm.sp = self.sp
        self.dm.messages = self.messages[:]


def send_message(msg, queue, context=None):
    """send_message.

    :param msg:
    :param queue:
    :param context:
    """
    with get_rabbitmq_conn(queue=queue, context=context) as conn:
        conn.send_message(queue, msg)


def queue_msg(msg, queue=None):
    """ Queues a rabbitmq message in the given queue
    """

    _mdm = MessagesDataManager()
    transaction.get().join(_mdm)
    _mdm.add(queue, msg)
