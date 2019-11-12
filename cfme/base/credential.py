from copy import deepcopy

from cfme.utils import conf
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


class FromConfigMixin(object):
    @staticmethod
    def rename_properties(creds):
        """
        helper function to make properties have same names in credential objects.
        Args:
            creds: dict

        Returns: updated dict
        """
        creds = deepcopy(creds)
        to_rename = [('password', 'secret'), ('username', 'principal')]
        for key1, key2 in to_rename:
            if key1 in creds:
                creds[key2] = creds[key1]
                del creds[key1]
        return creds

    @classmethod
    def from_config(cls, key):
        """
        helper function which allows to construct credential object from credentials.eyaml

        Args:
            key: credential key

        Returns: credential object
        """
        creds = cls.rename_properties(conf.credentials[key])
        return cls(**creds)

    @classmethod
    def from_plaintext(cls, creds):
        """
        helper function which allows to construct credential class from plaintext dict

        Args:
            creds: dict

        Returns: credential object
        """
        creds = cls.rename_properties(creds)
        return cls(**creds)


class Credential(Pretty, Updateable, FromConfigMixin):
    """
    A class to fill in credentials

    Args:
        principal: user name
        secret: password
        verify_secret: password
        domain: concatenated with principal if defined
    """
    pretty_attrs = ['principal', 'secret']

    def __init__(self, principal, secret, verify_secret=None, domain=None,
                 tenant_id=None, subscription_id=None, **ignore):
        self.principal = principal
        self.secret = secret
        self.verify_secret = verify_secret
        self.domain = domain
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id

    def __getattribute__(self, attr):
        if attr == 'verify_secret':
            if object.__getattribute__(self, 'verify_secret') is None:
                return object.__getattribute__(self, 'secret')
            else:
                return object.__getattribute__(self, 'verify_secret')

        elif attr == 'principal':
            domain = object.__getattribute__(self, 'domain')
            principal = object.__getattribute__(self, 'principal')
            return r'{}\{}'.format(domain, principal) if domain else principal
        else:
            return super(Credential, self).__getattribute__(attr)

    @property
    def view_value_mapping(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'username': self.principal,
            'password': self.secret,
            'confirm_password': None
        }

    def __eq__(self, other):
        if other is None:
            return False
        return self.principal == other.principal and self.secret == other.secret and \
            self.verify_secret == other.verify_secret

    def __ne__(self, other):
        return not self.__eq__(other)


class EventsCredential(Credential):
    pass


class CANDUCredential(Credential):
    pass


class AzureCredential(Credential):
    pass


class SSHCredential(Credential):
    @property
    def view_value_mapping(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'username': self.principal,
            'private_key': self.secret,
        }


class TokenCredential(Pretty, Updateable, FromConfigMixin):
    """
    A class to fill in credentials

    Args:
        token: identification token
        verify_token: token once more
    """
    pretty_attrs = ['token']

    def __init__(self, token, verify_token=None, **kwargs):
        self.token = token
        self.verify_token = verify_token
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __getattribute__(self, attr):
        if attr == 'verify_token':
            if object.__getattribute__(self, 'verify_token') is not None:
                return object.__getattribute__(self, 'verify_token')
            else:
                return object.__getattribute__(self, 'token')
        else:
            return super(TokenCredential, self).__getattribute__(attr)

    def __eq__(self, other):
        return self.token == other.token and self.verify_token == other.verify_token

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def view_value_mapping(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'token': self.token,
            'verify_token': None
        }


class ServiceAccountCredential(Pretty, Updateable):
    """
    A class to fill in credentials

    Args:
        service_account: service account string
    """
    pretty_attrs = ['service_account']

    def __init__(self, service_account):
        super(ServiceAccountCredential, self)
        self.service_account = service_account

    @property
    def view_value_mapping(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'service_account': self.service_account
        }

    def __eq__(self, other):
        return self.service_account == other.service_account

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_config(cls, key):
        # TODO: refactor this. consider json.dumps
        creds = deepcopy(conf.credentials[key])
        service_data = creds['service_account']
        service_account = '''
                  "type": "{type}",
                  "project_id": "{project}",
                  "private_key_id": "{private_key_id}",
                  "private_key": "{private_key}",
                  "client_email": "{email}",
                  "client_id": "{client}",
                  "auth_uri": "{auth}",
                  "token_uri": "{token}",
                  "auth_provider_x509_cert_url": "{auth_provider}",
                  "client_x509_cert_url": "{cert_url}"
                '''.format(
            type=service_data.get('type'),
            project=service_data.get('project_id'),
            private_key_id=service_data.get('private_key_id'),
            private_key=service_data.get('private_key').replace('\n', '\\n'),
            email=service_data.get('client_email'),
            client=service_data.get('client_id'),
            auth=service_data.get('auth_uri'),
            token=service_data.get('token_uri'),
            auth_provider=service_data.get('auth_provider_x509_cert_url'),
            cert_url=service_data.get('client_x509_cert_url'))
        service_account = '{' + service_account + '}'
        return cls(service_account=service_account)
