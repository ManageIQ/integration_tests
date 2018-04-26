import attr

from cfme.utils.providers import get_crud
from cfme.containers.provider.openshift import VirtualizationEndpoint
from . import InfraProvider


@attr.s(hash=False)
class KubeVirtProvider(InfraProvider):
    type_name = "kubevirt"
    settings_key = 'ems_kubevirt'
    mgmt_class = None

    parent_provider = attr.ib(default=None)

    def create(self, *args, **kwargs):
        # KubeVirt infra provider is automatically added in appliance when adding
        # a container provider, with selecting the virtualization option
        # so Override the standard behaviour to actually create the parent container provider first
        return self.parent_provider.create()

    @classmethod
    def from_config(cls, prov_config, prov_key):

        endpoints = {}
        token_creds = cls.process_credential_yaml_key(prov_config['credentials'], cred_type='token')
        for endp in prov_config['endpoints']:
            if VirtualizationEndpoint.name == endp:
                prov_config['endpoints'][endp]['token'] = token_creds.token
                endpoints[endp] = VirtualizationEndpoint(**prov_config['endpoints'][endp])

        parent_provider = get_crud(prov_config['parent_provider'])
        parent_provider.endpoints.update(endpoints)

        # passing virtualization of KubeVirt provider explicitly to ocp provider
        parent_provider.virt_type = prov_config['virt_type']

        return cls.appliance.collections.infra_providers.instantiate(
            prov_class=cls,
            name=prov_config.get('name'),
            key=prov_key,
            endpoints=endpoints,
            provider_data=prov_config,
            parent_provider=parent_provider)
