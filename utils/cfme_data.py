import warnings

from utils.conf import cfme_data

deprecated_warning = """"load_cfme_data is deprecated
please import cfme_data from utils.conf
"""


def load_cfme_data(filename=None):
    """Loads the cfme_data YAML"""
    warnings.warn(deprecated_warning, DeprecationWarning)
    return cfme_data
