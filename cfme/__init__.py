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

        self.details = {'button': True,
                        'principal': principal,
                        'secret': secret,
                        'verify_secret': verify_secret}
