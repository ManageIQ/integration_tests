from utils.pretty import Pretty


class Credential(Pretty):
    """
    A class to fill in credentials

    Args:
        principal: Something
        secret: Something
        verify_secret: Something
    """
    pretty_attrs = ['principal', 'secret']

    def __init__(self, principal=None, secret=None, verify_secret=None, **ignore):
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
        elif attr == "verify_token":
            try:
                vs = object.__getattribute__(self, 'verify_token')
            except AttributeError:
                return object.__getattribute__(self, 'token')
        else:
            return object.__getattribute__(self, attr)
