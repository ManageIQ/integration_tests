"this file is a hack to keep prt alive"
import sys
import warnings
from cfme import utils


warnings.warn('bad import of utils')
sys.modules[__name__] = utils
