import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.provider_views import CloudProviderEditView
from cfme.web_ui import flash
from utils import testgen, error
from utils.conf import cfme_data, credentials
from utils.log import logger
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(1),
    test_requirements.proxy,
    pytest.mark.usefixtures('setup_provider_modscope')
]
pytest_generate_tests = testgen.generate([AzureProvider, GCEProvider, EC2Provider],
                                         scope="module")


def settings_local(appliance, proxy_type, valid=True):
    """Creates the file string and sends it to the appliance.  If more than one provider,
        It loops through each item in proxy_type

        Args: provider_type - is a list that is either or more provider.type and/or 'default'
              valid - determines if we want the proxy to pass or fail.

    """
    proxy = cfme_data['proxy_servers']['default']
    creds = credentials[proxy['credentials']]
    port = proxy['port'] if valid else '8686'

    for each_proxy in proxy_type:
        data_dict = {'http_proxy':
                        {str(each_proxy):
                            {'host': proxy['host'],
                             'port': port,
                             'user': creds['username'],
                             'password': creds['password']}}}
    logger.info("Proxy Dictionary equals: {}".format(data_dict))
    appliance.set_yaml_settings_local(data_dict)
    appliance.restart_evm_service(wait_for_web_ui=True)


def reset_proxy_settings(appliance, proxy_type, provider):
    """Clears the file string and sends it to the appliance

        Args: proxy_type - is a list that is either or more provider.type and/or 'default'
              We have to explicity clear each change as the values are cached at restart.
    """
    appliance.remove_yaml_settings_local()
    try:
        validate_provider(appliance, provider)
    except Exception:
        pass
    appliance.server.logout()
   

def validate_provider(appliance, provider):
    """Navigates to the provider and clicks the validate button for immediate response"""
    view = navigate_to(provider, 'EditFromDetails')
    view.validate.click()


def test_proxy_default(appliance, provider, request):
    """Configures the specific valid proxy for each provider"""
    logger.info("Begin Test Valid Default Proxy for Provider {}".format(provider.type))

    @request.addfinalizer
    def _cleanup_proxy():
        reset_proxy_settings(appliance, ['default'], provider)

    logger.info("Test to fail first")
    settings_local(appliance, ["default"], False)
    try:
        with error.expected('Credential validation was not successful:'):
            validate_provider(appliance, provider)
            flash.assert_message_match('Credential validation was successful')
    except Exception: 
        pass    
    appliance.server.logout()

    logger.info("Then test to pass")
    settings_local(appliance, ['default'], True)
    appliance.restart_evm_service(wait_for_web_ui=True)
    validate_provider(appliance, provider)
    flash.assert_message_match('Credential validation was successful')
    appliance.server.logout()


def test_proxy_valid(appliance, provider, request):
    """Configures the specific valid proxy for each provider"""
    logger.info("Begin Test Valid Proxy for Provider {}".format(provider.type))

    settings_local(appliance, [provider.type], True)
    validate_provider(appliance, provider)
    flash.assert_message_match('Credential validation was successful')
    appliance.server.logout()


def test_proxy_invalid(appliance, provider, request):
    """Configures the specific invalid proxy for each provider"""
    logger.info("Begin Test Invalid Proxy for Provider {}".format(provider.type))

    @request.addfinalizer
    def _cleanup_proxy():
        reset_proxy_settings(appliance, [provider.type], provider)

    settings_local(appliance, [provider.type], False)
    try:
        with error.expected('Credential validation was not successful:'):
            validate_provider(appliance, provider)
            flash.assert_message_match('Credential validation was successful')
    except Exception: 
        pass    
    appliance.server.logout()


def test_proxy_override(appliance, provider, request):
    """ Configures a bad default and then a valid proxy for each provider
        This one is a little weird because all the other tests setup a specific provider, but
        this one needs to setup the default incorrectly and the provider correctly so that we know
        the provider proxy was definitely being used and not the default.
    """
    logger.info("Begin Test Override Proxy for Provider {}".format(provider.type))

    @request.addfinalizer
    def _cleanup_proxy():
        reset_proxy_settings(appliance, ['default', provider.type], provider)

    logger.info("Test to fail first")
    settings_local(appliance, ["default"], False)
    appliance.restart_evm_service(wait_for_web_ui=True)
    with error.expected('Credential validation was not successful:'):
        validate_provider(appliance, provider)
        flash.assert_message_match('Credential validation was successful')

    logger.info("Then test to pass using provider specific override")
    appliance.server.logout()
    settings_local(appliance, ['default', provider.type], True)
    appliance.restart_evm_service(wait_for_web_ui=True)
    validate_provider(appliance, provider)
    flash.assert_message_match('Credential validation was successful')
    appliance.server.logout()
