# -*- coding: utf-8 -*-
from cfme.web_ui import FileInput, Input, Radio, form_buttons
from cfme.web_ui.tabstrip import TabStripForm
from utils.pretty import Pretty
from utils.update import Updateable


class Credential(Pretty, Updateable):
    """
    A class to fill in credentials

    Args:
        principal: Something
        secret: Something
        verify_secret: Something
    """
    pretty_attrs = ['principal', 'secret']

    def __init__(self, principal, secret, verify_secret=None, domain=None, **ignore):
        self.principal = principal
        self.secret = secret
        self.verify_secret = verify_secret
        self.domain = domain

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

    def as_dict(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'principal': self.principal,
            'secret': self.secret,
            'verify_secret': self.verify_secret
        }

    @property
    def form(self):
        return provider_credential_form()


class AMQPCredential(Credential):
    pass


class CANDUCredential(Credential):
    pass


class AzureCredential(Credential):
    pass


class SSHCredential(Credential):
    pass


class TokenCredential(Pretty, Updateable):
    """
    A class to fill in credentials

    Args:
        token: Something
        verify_token: Something
    """
    pretty_attrs = ['token']

    def __init__(self, token, verify_token=None):
        self.token = token
        self.verify_token = verify_token

    def __getattribute__(self, attr):
        if attr == 'verify_token':
            if object.__getattribute__(self, 'verify_token') is not None:
                return object.__getattribute__(self, 'verify_token')
            else:
                return object.__getattribute__(self, 'token')
        else:
            return super(TokenCredential, self).__getattribute__(attr)

    def as_dict(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'token': self.token,
            'verify_token': self.verify_token
        }

    @property
    def form(self):
        return provider_credential_form()


class ServiceAccountCredential(Pretty, Updateable):
    """
    A class to fill in credentials

    Args:
        service_account: Something
    """
    pretty_attrs = ['service_account']

    def __init__(self, service_account):
        super(ServiceAccountCredential, self)
        self.service_account = service_account

    def as_dict(self):
        """
        used for filling forms like add/edit provider form
        Returns: dict
        """
        return {
            'service_account': self.service_account
        }

    @property
    def form(self):
        return provider_credential_form()


def provider_credential_form():
    # todo: to remove it when all providers are moved to widgetastic
    fields = [
        ('token_secret_55', Input('bearer_token')),
        ('google_service_account', Input('service_account')),
    ]
    tab_fields = {
        ("Default", ('default_when_no_tabs', )): [
            ('default_principal', Input("default_userid")),
            ('default_secret', Input("default_password")),
            ('default_verify_secret', Input("default_verify")),
            ('token_secret', Input('default_password')),
            ('token_verify_secret', Input('default_verify')),
        ],

        "RSA key pair": [
            ('ssh_user', Input("ssh_keypair_userid")),
            ('ssh_key', FileInput("ssh_keypair_password")),
        ],

        "C & U Database": [
            ('candu_principal', Input("metrics_userid")),
            ('candu_secret', Input("metrics_password")),
            ('candu_verify_secret', Input("metrics_verify")),
        ],

        "Hawkular": [
            ('hawkular_validate_btn', form_buttons.validate),
        ]
    }
    fields_end = [
        ('validate_btn', form_buttons.validate),
    ]

    tab_fields["Events"] = []
    tab_fields["Events"].extend([
        ('event_selection', Radio('event_stream_selection')),
        ('amqp_principal', Input("amqp_userid")),
        ('amqp_secret', Input("amqp_password")),
        ('amqp_verify_secret', Input("amqp_verify")),
    ])

    return TabStripForm(fields=fields, tab_fields=tab_fields, fields_end=fields_end)
