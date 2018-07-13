"""For method related to multiprocessing, for reducing code duplication"""

from multiprocessing import Pool

from cfme.utils.log import logger


def pool_manager(func=None,  func_list=None, arg_list=None, pool_size=8, count=0):
    """Create a process pool via list of argument tuples and join the processes via apply_async

    Notes:
        Use Manager.Queue for any queues in the arg_list tuples.
        BLOCKS by joining
        TODO kwargs in arg_list tuples

    Args:
        func (method): A function to parallel process
        arg_list (list): a list of arg tuples
        pool_size: integer number of pool workers
        count: number of times to run func if no args passed
        func_list: list of funcs to run in pool, no args.

    Returns:
        list of the return values from apply_async
    """
    if (func and func_list) or (func_list and count):
        raise ValueError('pool_manager called with wrong options')

    proc_pool = Pool(pool_size)
    proc_results = []
    if func and arg_list:
        proc_results = [proc_pool.apply_async(func, args=arg_tuple) for arg_tuple in arg_list]
    elif func and count:
        proc_results = [proc_pool.apply_async(func) for _ in range(0, count)]
    elif func_list:
        [proc_pool.apply_async(funct) for funct in func_list]

    proc_pool.close()
    proc_pool.join()

    def _get_result(proc):
        """Check for exceptions since they're captured

        Don't care about non-exception results since all non-exception results are in the queues
        """
        try:
            return proc.get()
        except Exception as ex:
            logger.exception('Exception during function call %r', func.__name__)
            return ex

    return [_get_result(pr) for pr in proc_results]