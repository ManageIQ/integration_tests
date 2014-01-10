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

    def fill(self, set_principal_fn, set_secret_fn, set_verify_fn):
        set_principal_fn(self.principal)
        set_secret_fn(self.secret)
        set_verify_fn(self.verify_secret or self.secret)
