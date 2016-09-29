import warnings

from debtcollector.removals import remove


warnings.simplefilter('once', category=DeprecationWarning)

removed_in_fw30 = remove(
    removal_version="framework 3.0",
)
