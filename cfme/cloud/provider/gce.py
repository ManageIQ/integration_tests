import attr
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from wrapanapi.systems import GoogleCloudSystem

from . import CloudProvider
from cfme.base.credential import ServiceAccountCredential
from cfme.cloud.instance.gce import GCEInstance
from cfme.common.provider import DefaultEndpoint
from cfme.services.catalogs.catalog_items import GoogleCatalogItem


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


@attr.s(cmp=False)
class GCEProvider(CloudProvider):
    """
     BaseProvider->CloudProvider->GCEProvider class.
     represents CFME provider and operations available in UI
    """
    catalog_item_type = GoogleCatalogItem
    type_name = "gce"
    mgmt_class = GoogleCloudSystem
    vm_class = GCEInstance
    db_types = ["Google::CloudManager"]
    endpoints_form = GCEEndpointForm
    settings_key = 'ems_google'

    project = attr.ib(default=None)
    region = attr.ib(default=None)
    region_name = attr.ib(default=None)

    @property
    def view_value_mapping(self):
        endpoints = {
            'name': self.name,
            'prov_type': 'Google Compute Engine',
            'region': self.region_name,
            'project_id': self.project
        }

        if self.appliance.version >= '5.9.2':
            # from 5.9.2 we are not supporting region selection for GCE
            del endpoints['region']
        return endpoints

    @classmethod
    def from_config(cls, prov_config, prov_key):
        endpoint = GCEEndpoint(**prov_config['endpoints']['default'])
        return cls.appliance.collections.cloud_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            project=prov_config['project'],
            zone=prov_config['zone'],
            region=prov_config['region'],
            region_name=prov_config['region_name'],
            endpoints={endpoint.name: endpoint},
            key=prov_key)

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
