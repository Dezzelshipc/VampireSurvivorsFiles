import unittest

import multirun_tests, unpacker_open_tests


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(multirun_tests))
    suite.addTests(loader.loadTestsFromModule(unpacker_open_tests))

    return suite


if __name__ == '__main__':
    unittest.main()
