from wrapanapi.google import GoogleCloudSystem
from widgetastic.widget import View
from widgetastic_patternfly import Button, Input

from cfme.base.credential import ServiceAccountCredential
from cfme.common.provider import DefaultEndpoint
from . import CloudProvider


class GCEEndpoint(DefaultEndpoint):
    """
     represents default GCE endpoint (Add/Edit dialogs)
    """
    credential_class = ServiceAccountCredential

    @property
    def view_value_mapping(self):
        return {}


class GCEEndpointForm(View):
    """
     represents default GCE endpoint form in UI (Add/Edit dialogs)
    """
    service_account = Input('service_account')
    validate = Button('Validate')


class GCEProvider(CloudProvider):
    """
     BaseProvider->CloudProvider->GCEProvider class.
     represents CFME provider and operations available in UI
    """
    type_name = "gce"
    mgmt_class = GoogleCloudSystem
    db_types = ["Google::CloudManager"]
    endpoints_form = GCEEndpointForm

    def __init__(self, name=None, project=None, zone=None, region=None, region_name=None,
                 endpoints=None, key=None, appliance=None):
        super(GCEProvider, self).__init__(name=name, zone=zone, key=key, endpoints=endpoints,
                                          appliance=appliance)
        self.region = region
        self.region_name = region_name
        self.project = project

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Google Compute Engine',
            'region': self.region_name,
            'project_id': self.project
        }

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = GCEEndpoint(**prov_config['endpoints']['default'])
        return cls(name=prov_config['name'],
                   project=prov_config['project'],
                   zone=prov_config['zone'],
                   region=prov_config['region'],
                   region_name=prov_config['region_name'],
                   endpoints={endpoint.name: endpoint},
                   key=prov_key,
                   appliance=appliance)

    @classmethod
    def get_credentials(cls, credential_dict, cred_type=None):
        """Processes a credential dictionary into a credential object.

        Args:
            credential_dict: A credential dictionary.
            cred_type: Type of credential (None, token, ssh, amqp, ...)

        Returns:
            A :py:class:`cfme.base.credential.ServiceAccountCredential` instance.
        """
        return ServiceAccountCredential.from_config(credential_dict)
