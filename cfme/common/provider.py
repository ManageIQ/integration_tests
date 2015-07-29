from utils import conf
from cfme.exceptions import (
    ProviderHasNoKey
)
from utils.providers import provider_factory
from utils.log import logger


class BaseProvider():

    @property
    def data(self):
        return self.get_yaml_data()

    @property
    def mgmt(self):
        return self.get_mgmt_system()

    @property
    def type(self):
        return self.data['type']

    @property
    def version(self):
        return self.data['version']

    def get_yaml_data(self):
        """ Returns yaml data for this provider.
        """
        if hasattr(self, 'provider_data') and self.provider_data is not None:
            return self.provider_data
        elif self.key is not None:
            return conf.cfme_data['management_systems'][self.key]
        else:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get yaml data', self.name)

    def get_mgmt_system(self):
        """ Returns the mgmt_system using the :py:func:`utils.providers.provider_factory` method.
        """
        if hasattr(self, 'provider_data') and self.provider_data is not None:
            return provider_factory(self.provider_data)
        elif self.key is not None:
            return provider_factory(self.key)
        else:
            raise ProviderHasNoKey('Provider %s has no key, so cannot get mgmt system')


def cleanup_vm(vm_name, provider):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider.key))
        provider.mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider.key))
