from wait_for import wait_for as wait_for_mod
from wait_for import RefreshTimer, TimedOutError  # NOQA
from utils.log import logger
from functools import partial

wait_for = partial(wait_for_mod, logger=logger)
