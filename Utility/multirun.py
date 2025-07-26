from asyncio import run, gather, to_thread
from multiprocessing import Pool
from typing import Callable, Iterable, Awaitable

from Config.config import Config
from Utility.constants import IS_DEBUG


def run_multiprocess[** P, T](func: Callable[P, T], args: Iterable[P.args], is_many_args=True, is_multiprocess=True,
                              processes=None, is_generator=False) -> list[T]:
    """
    Applies sync function to list of arguments in multiprocessing environment and returns list of results

    :param func: Sync function that takes arguments P (can be a tuple) and returns T
    :param args: Iterable of arguments type P
    :param is_many_args: Should be set to False when args is a list of values. Default: True
    :param is_multiprocess: When set to False, disables multiprocessing environment and instead calls list comprehension. Default: True
    :param processes: Number of processes to use. Default: None (auto)
    :param is_generator: When is_generator==True and is_multiprocess==False then list generator will be returned. Default: False
    :return: List of functions results
    """
    is_config_mp = Config().get_multiprocessing() and not IS_DEBUG

    if is_multiprocess and is_config_mp:
        with Pool(processes) as p:
            if is_many_args:
                return p.starmap(func, args)
            else:
                return p.map(func, args)
    else:
        gen = (is_many_args and func(*arg) or func(arg) for arg in args)
        return gen if is_generator else list(gen)


def run_multiprocess_single[** P, T](func: Callable[P, T], args: Iterable[P.args], is_multiprocess=True,
                                     processes=None) -> list[T]:
    return run_multiprocess(func, args, is_multiprocess=is_multiprocess, processes=processes, is_many_args=False)


async def __run_sync_in_async[** P, T](func: Callable[P, Awaitable[T]], args: Iterable[P.args]) -> list[T]:
    return await gather(
        *[isinstance(arg, Iterable) and to_thread(func, *arg) or to_thread(func, arg) for arg in args])


async def __run_async_in_async[** P, T](func: Callable[P, Awaitable[T]], args: Iterable[P.args]) -> list[T]:
    return await gather(*[isinstance(arg, Iterable) and func(*arg) or func(arg) for arg in args])


def run_concurrent_sync[** P, T](func: Callable[P, T], args: Iterable[P.args]) -> list[T]:
    """
    Applies sync function to list of arguments in async environment and returns list of results

    args can be a list of values (ex: [1, 2, 3]) or list of tuples ([(1,2), (2,3)])

    :param func: Sync function that takes arguments P (can be a tuple) and returns T
    :param args: Iterable of arguments type P
    :return: List of functions results
    """
    return run(__run_sync_in_async(func, args))


def run_concurrent_async[** P, T](func: Callable[P, Awaitable[T]], args: Iterable[P.args]) -> list[T]:
    """
    Applies async function to list of arguments in async environment and returns list of results

    args can be a list of values (ex: [1, 2, 3]) or list of tuples ([(1,2), (2,3)])

    :param func: Sync function that takes arguments P (can be a tuple) and returns T
    :param args: Iterable of arguments type P
    :return: List of functions results
    """
    return run(__run_async_in_async(func, args))


def run_gather[T](*funcs: Iterable[Callable[..., Awaitable[T]]]) -> list[T]:
    """
    Runs asyncio.gather(*f) for async functions in sync environment and returns list of results

    :param funcs: Iterable of called async functions
    :return: List of function results
    """

    async def _gather(*f):
        return await gather(*f)

    return run(_gather(*funcs))
