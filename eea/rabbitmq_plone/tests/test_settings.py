import unittest


class TestProgramUnit(unittest.TestCase):
    """Unit test for the Program type
    """

    def test_catalog(self):

        self.assertEqual(6, 6)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
