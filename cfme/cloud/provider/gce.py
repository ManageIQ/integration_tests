from mgmtsystem.google import GoogleCloudSystem

import cfme
import cfme.base.credential
import cfme.fixtures.pytest_selenium as sel
from . import CloudProvider


class GCEProvider(CloudProvider):
    type_name = "gce"
    mgmt_class = GoogleCloudSystem
    db_types = ["Google::CloudManager"]

    def __init__(
            self, name=None, project=None, zone=None, region=None, credentials=None, key=None,
            appliance=None):
        super(GCEProvider, self).__init__(
            name=name, zone=zone, key=key, credentials=credentials, appliance=appliance)
        self.region = region
        self.project = project

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Google Compute Engine',
                'google_region_select': sel.ByValue(kwargs.get('region')),
                'google_project_text': kwargs.get('project')}

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        sa_creds = cls.get_credentials_from_config(prov_config['credentials'],
                                                   cred_type='service_account')
        return cls(name=prov_config['name'],
                   project=prov_config['project'],
                   zone=prov_config['zone'],
                   region=prov_config['region'],
                   credentials={'service_account': sa_creds},
                   key=prov_key,
                   appliance=appliance)

    @classmethod
    def get_credentials(cls, credential_dict, cred_type=None):
        """Processes a credential dictionary into a credential object.

        Args:
            credential_dict: A credential dictionary.
            cred_type: Type of credential (None, token, ssh, amqp, ...)

        Returns:
            A :py:class:`BaseProvider.Credential` instance.
        """
        service_account = credential_dict.get('service_account', None)
        service_account = cls.gce_service_account_formating(service_account)
        return cfme.base.credential.ServiceAccountCredential(service_account=service_account)

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
