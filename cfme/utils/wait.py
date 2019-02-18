from functools import partial

from wait_for import RefreshTimer  # noqa: F401
from wait_for import TimedOutError  # noqa: F401
from wait_for import wait_for as wait_for_mod
from wait_for import wait_for_decorator as wait_for_decorator_mod

from cfme.utils.log import logger

wait_for = partial(wait_for_mod, logger=logger)
wait_for_decorator = partial(wait_for_decorator_mod, logger=logger)
