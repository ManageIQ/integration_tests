"""
cfme
----
"""


class Credential(object):
    """
    A class to fill in credentials

    Args:
        principal: Something
        secret: Something
        verify_secret: Something
    """

    def __init__(self, principal=None, secret=None, verify_secret=None):
        self.principal = principal
        self.secret = secret
        self.verify_secret = verify_secret

    def __getattribute__(self, attr):
        if attr == 'verify_secret':
            vs = object.__getattribute__(self, 'verify_secret')
            if vs is None:
                return object.__getattribute__(self, 'secret')
            else:
                return vs
        else:
            return object.__getattribute__(self, attr)
