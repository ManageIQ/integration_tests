import os

import yaml
from py.path import local

def load_credentials(filename=None):
    if filename is None:
        this_file = os.path.abspath(__file__)
        path = local(this_file).new(basename='../credentials.yaml')
    else:
        path = local(filename)
    if path.check():
        credentials_fh = path.open()
        credentials_dict = yaml.load(credentials_fh)
        return credentials_dict
    else:
        msg = 'Usable to load credentials file at %s' % path
        raise Exception(msg)

