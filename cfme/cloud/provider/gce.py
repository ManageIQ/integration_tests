from riggerlib import recursive_update
from widgetastic.widget import View
from widgetastic_patternfly import Button, Input
from wrapanapi.google import GoogleCloudSystem

from cfme.base.credential import ServiceAccountCredential
from cfme.common.provider import DefaultEndpoint
from cfme.services.catalogs.catalog_items import GoogleCatalogItem
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
    catalog_item_type = GoogleCatalogItem
    type_name = "gce"
    mgmt_class = GoogleCloudSystem
    db_types = ["Google::CloudManager"]
    endpoints_form = GCEEndpointForm
    settings_key = 'ems_google'

    def __init__(self, name=None, project=None, zone=None, region=None, region_name=None,
                 endpoints=None, key=None, appliance=None):
        super(GCEProvider, self).__init__(name=name, zone=zone, key=key, endpoints=endpoints,
                                          appliance=appliance)
        self.region = region
        self.region_name = region_name
        self.project = project

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

    @property
    def vm_default_args(self):
        """Represents dictionary used for Vm/Instance provision with GCE mandatory default args"""
        inst_args = super(GCEProvider, self).vm_default_args
        provisioning = self.data['provisioning']
        recursive_update(inst_args, {
            'properties': {
                'boot_disk_size': provisioning.get('boot_disk_size')}
        })
        return inst_args

    @property
    def vm_default_args_rest(self):
        inst_args = super(GCEProvider, self).vm_default_args_rest
        provisioning = self.data['provisioning']
        recursive_update(inst_args, {
            'vm_fields': {
                'boot_disk_size': provisioning['boot_disk_size'].replace(' ', '.')}})
        return inst_args
