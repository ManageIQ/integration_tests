import attr
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from wrapanapi.systems import GoogleCloudSystem

from cfme.base.credential import ServiceAccountCredential
from cfme.cloud.instance.gce import GCEInstance
from cfme.cloud.provider import CloudProvider
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
    ems_pretty_name = 'Google Compute Engine'

    project = attr.ib(default=None)
    region = attr.ib(default=None)  # deprecated in 5.9.2
    region_name = attr.ib(default=None)  # deprecated in 5.9.2

    @property
    def view_value_mapping(self):
        endpoints = {
            'name': self.name,
            'prov_type': 'Google Compute Engine',
            'project_id': self.project
        }

        return endpoints

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        appliance = appliance if appliance is not None else cls.appliance
        endpoint = GCEEndpoint(**prov_config['endpoints']['default'])
        return appliance.collections.cloud_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            project=prov_config['project'],
            zone=prov_config['zone'],
            region=prov_config.get('region'),
            region_name=prov_config.get('region_name'),
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
