"""parallelizer hooks

Custom hooks to help keep runtime ordering straight with regard to the parallelizer's state

"""


def pytest_parallel_configured(parallel_session):
    """called after the parallel session is configured

    This is *always* called, whether running parallel or not.

    If running standalone, ``parallel_session`` will be None.

    """
