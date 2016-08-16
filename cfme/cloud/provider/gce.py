from __future__ import unicode_literals
from mgmtsystem.google import GoogleCloudSystem
from . import Provider
import cfme.fixtures.pytest_selenium as sel


@Provider.add_type_map
class GCEProvider(Provider):
    type_name = "gce"
    mgmt_class = GoogleCloudSystem

    def __init__(self, name=None, project=None, zone=None, region=None, credentials=None, key=None):
        super(GCEProvider, self).__init__(name=name, zone=zone, key=key, credentials=credentials)
        self.region = region
        self.project = project

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Google Compute Engine',
                'google_region_select': sel.ByValue(kwargs.get('region')),
                'google_project_text': kwargs.get('project')}

    @classmethod
    def configloader(cls, prov_config, prov_key):
        ser_acc_creds = cls.get_credentials_from_config(
            prov_config['credentials'], cred_type='service_account')
        return cls(name=prov_config['name'],
            project=prov_config['project'],
            zone=prov_config['zone'],
            region=prov_config['region'],
            credentials={'default': ser_acc_creds},
            key=prov_key)

    @classmethod
    def get_credentials(cls, credential_dict, cred_type=None):
        """Processes a credential dictionary into a credential object.

        Args:
            credential_dict: A credential dictionary.
            cred_type: Type of credential (None, token, ssh, amqp, ...)

        Returns:
            A :py:class:`BaseProvider.Credential` instance.
        """
        domain = credential_dict.get('domain', None)
        token = credential_dict.get('token', None)
        service_account = credential_dict.get('service_account', None)
        if service_account:
            service_account = cls.gce_service_account_formating(service_account)
        return cls.Credential(
            principal=credential_dict['username'],
            secret=credential_dict['password'],
            cred_type=cred_type,
            domain=domain,
            token=token,
            service_account=service_account)

    @staticmethod
    def gce_service_account_formating(data):
        service_data = '''
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
            type=data.get('type'),
            project=data.get('project_id'),
            private_key_id=data.get('private_key_id'),
            private_key=data.get('private_key').replace('\n', '\\n'),
            email=data.get('client_email'),
            client=data.get('client_id'),
            auth=data.get('auth_uri'),
            token=data.get('token_uri'),
            auth_provider=data.get('auth_provider_x509_cert_url'),
            cert_url=data.get('client_x509_cert_url'))
        return '{' + service_data + '}'
