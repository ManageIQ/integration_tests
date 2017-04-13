from cfme.base.credential import Credential, CANDUCredential, EventsCredential, SSHCredential, \
    TokenCredential
from utils import version


class DefaultEndpoint(object):
    credential_class = Credential
    name = 'default'

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            if key == 'credentials' and not isinstance(val, (Credential, TokenCredential)):
                val = self.credential_class.from_config(val)
            setattr(self, key, val)

    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname}


class VirtualCenterEndpoint(DefaultEndpoint):
    pass


class SCVMMEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'security_protocol': self.security_protocol,
                'realm': self.security_realm
                }


class RHEVMEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'api_port': self.api_port,
                'verify_tls': version.pick({version.LOWEST: None,
                                            '5.8': self.verify_tls}),
                'ca_certs': version.pick({version.LOWEST: None,
                                          '5.8': self.ca_certs})
                }


class RHOSEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'api_port': self.api_port,
                'security_protocol': self.security_protocol,
                }


class CANDUEndpoint(DefaultEndpoint):
    credential_class = CANDUCredential
    name = 'candu'

    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'api_port': self.api_port,
                'database_name': self.database}


class EventsEndpoint(DefaultEndpoint):
    credential_class = EventsCredential
    name = 'events'

    @property
    def view_value_mapping(self):
        return {'event_stream': self.event_stream,
                'security_protocol': self.security_protocol,
                'hostname': self.hostname,
                'api_port': self.api_port,
                }


class SSHEndpoint(DefaultEndpoint):
    credential_class = SSHCredential
    name = 'rsa_keypair'

    @property
    def view_value_mapping(self):
        return {}


class HawkularEndpoint(DefaultEndpoint):
    credential_class = TokenCredential
    pass
