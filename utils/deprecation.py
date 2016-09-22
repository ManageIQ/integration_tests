import warnings
from functools import partial
from debtcollector.removals import remove, removed_class


warnings.simplefilter('once', category=DeprecationWarning)

removed_in_fw30 = remove(removal_version="framework 3.0")
removed_class_in_fw30 = partial(removed_class, removal_version="framework 3.0")
