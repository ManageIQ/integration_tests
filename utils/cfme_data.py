import os

import yaml
from py.path import local

from utils.randomness import RandomizeValues

def load_cfme_data(filename=None):
    """Loads the cfme_data YAML from the given filename

    If the filename is omitted or None, attempts will be made to load it from
    its normal location in the parent of the utils directory.

    The cfme_data dict loaded with this method supports value randomization,
    thanks to the RandomizeValues class. See that class for possible options

    Example usage in cfme_data.yaml (quotes are important!):

    top_level:
        list:
            - "{random_str}"
            - "{random_int}"
            - "{random_uuid}"
        random_thing: "{random_string:24}"

    """
    if filename is None:
        this_file = os.path.abspath(__file__)
        path = local(this_file).new(basename='../cfme_data.yaml')
    else:
        path = local(filename)

    if path.check():
        cfme_data_fh = path.open()
        cfme_data_dict = yaml.load(cfme_data_fh)
        return RandomizeValues.from_dict(cfme_data_dict)
    else:
        msg = 'Usable to load cfme_data file at %s' % path
        raise Exception(msg)

