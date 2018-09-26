import unittest


class TestSettings(unittest.TestCase):
    """Unit test for the Program type
    """

    def test_interfaces(self):
        try:
            from eea.rabbitmq.plone.interfaces.layers import \
                    IEEARabbitMQPloneInstalled
        except Exception:
            IEEARabbitMQPloneInstalled = None
        self.assertTrue(IEEARabbitMQPloneInstalled is not None)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
