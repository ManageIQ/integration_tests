from wait_for import wait_for as wait_for_mod, wait_for_decorator as wait_for_decorator_mod
from wait_for import RefreshTimer, TimedOutError  # NOQA
from cfme.utils.log import logger
from functools import partial

wait_for = partial(wait_for_mod, logger=logger)
wait_for_decorator = partial(wait_for_decorator_mod, logger=logger)
