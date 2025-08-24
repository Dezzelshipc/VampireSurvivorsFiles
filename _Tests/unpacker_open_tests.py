from unittest import TestCase, main as ut_main

import unpacker


class UnpackerOpenTest(TestCase):
    def test_unpacker_open(self):
        unp = unpacker.Unpacker()
        self.assertEqual(unp.state(), "normal")

if __name__ == "__main__":
    ut_main()