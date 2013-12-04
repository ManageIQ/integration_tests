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


class Credential(object):
    """
    """
    
    def __init__(self, principal=None, secret=None, verify_secret=None):
        """
        
        Arguments:
        - `principal`:
        - `secret`:
        - `verify_secret`:
        """
        self.principal = principal
        self.secret = secret
        self.verify_secret = verify_secret

    def fill(self, set_principal_fn, set_secret_fn, set_verify_fn):
        set_principal_fn(self.principal)
        set_secret_fn(self.secret)
        set_verify_fn(self.verify_secret or self.secret)

    

