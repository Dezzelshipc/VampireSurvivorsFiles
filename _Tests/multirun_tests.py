import asyncio
from typing import Iterable
from unittest import TestCase, main as ut_main

from Utility.multirun import run_multiprocess, run_concurrent_sync, run_gather


def many_args(a: int, b: int, c: int) -> int:
    return 3 * a + 7 * b + 13 * c


def single_arg(a: int) -> int:
    return 101 * a


class _TestRunsTests(TestCase):
    """
    Correct sync implementation of other multirun functions
    """

    @staticmethod
    def _run_test(func, args):
        return [isinstance(arg, Iterable) and func(*arg) or func(arg) for arg in args]

    def test_many_args(self):
        args = [(n, n - 1, n - 2) for n in range(10)]
        ret = self._run_test(many_args, args)
        expected = [many_args(*a) for a in args]
        self.assertEqual(ret, expected)

    def test_single_args(self):
        args = [*range(10)]
        ret = self._run_test(single_arg, args)
        expected = [single_arg(a) for a in args]
        self.assertEqual(ret, expected)


class MultiprocessTests(TestCase):
    def test_mp_many_args(self):
        args = [(n, n - 1, n - 2) for n in range(10)]
        ret = run_multiprocess(many_args, args)
        expected = [many_args(*a) for a in args]
        self.assertEqual(ret, expected)

    def test_mp_single_args(self):
        args = [n for n in range(10)]
        ret = run_multiprocess(single_arg, args, is_many_args=False)
        expected = [single_arg(a) for a in args]
        self.assertEqual(ret, expected)

    def test_no_mp_many_args(self):
        args = [(n, n - 1, n - 2) for n in range(10)]
        ret = run_multiprocess(many_args, args, is_multiprocess=False)
        expected = [many_args(*a) for a in args]
        self.assertEqual(ret, expected)

    def test_no_mp_single_args(self):
        args = [n for n in range(10)]
        ret = run_multiprocess(single_arg, args, is_many_args=False, is_multiprocess=False)
        expected = [single_arg(a) for a in args]
        self.assertEqual(ret, expected)


class ConcurrentTests(TestCase):
    def test_cc_many_args(self):
        args = [(n, n - 1, n - 2) for n in range(10)]
        ret = run_concurrent_sync(many_args, args)
        expected = [many_args(*a) for a in args]
        self.assertEqual(ret, expected)

    def test_cc_single_args(self):
        args = [*range(10)]
        ret = run_concurrent_sync(single_arg, args)
        expected = [single_arg(a) for a in args]
        self.assertEqual(ret, expected)


class RunGather(TestCase):
    @staticmethod
    async def _add_a(a, b) -> int:
        await asyncio.sleep(0.1)
        return a + b

    @staticmethod
    def _add_s(a, b) -> int:
        return a + b

    def test_gather(self):
        to_add = [(n, 2 * n) for n in range(10)]
        ret = run_gather(*[self._add_a(a, b) for a, b in to_add])
        expected = [self._add_s(a, b) for a, b in to_add]
        self.assertEqual(ret, expected)


if __name__ == "__main__":
    ut_main()
