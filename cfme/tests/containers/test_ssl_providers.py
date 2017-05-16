import pytest
from itertools import product
from cfme.containers.provider import ContainersProvider
from cfme.common.provider import get_certificate
from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to
from cfme.web_ui import fill, flash
from cfme.fixtures import pytest_selenium as sel


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.8.0.3")]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')

DEFAULT_SEC_PROTOCOLS = 'SSL trusting custom CA', 'SSL without validation', 'SSL'
HAWKULAR_SEC_PROTOCOLS = 'SSL trusting custom CA', 'SSL without validation', 'SSL'


@pytest.mark.parametrize('default_sec_protocols', DEFAULT_SEC_PROTOCOLS)
@pytest.mark.usefixtures('has_no_containers_providers')
@pytest.mark.polarion('CMP-10586')
def test_add_provider_ssl(provider, default_sec_protocols, soft_assert):
    """ This test checks adding container providers with 3 different security protocols:
    SSL trusting custom CA, SSL without validation and SSL
        """
    navigate_to(ContainersProvider, 'Add')
    fill(provider.properties_form, form_data(provider, default_sec_protocol=default_sec_protocols))
    for cred in provider.credentials:
        try:
            fill(provider.credentials[cred].form, provider.credentials[cred], validate=True)
            provider._submit(False, provider.add_provider_button)
            flash.assert_message_contain('Containers Providers "' + provider.name + '" was saved')
        except:
            # The refresh is a workaround for
            # https://github.com/ManageIQ/integration_tests/issues/4478
            sel.refresh()
            soft_assert(False, provider.name + ' wasn\'t added successfully using ' +
                        default_sec_protocols + ' security')


@pytest.mark.parametrize(('default_sec_protocols', 'hawkular_sec_protocols'),
                         product(DEFAULT_SEC_PROTOCOLS, HAWKULAR_SEC_PROTOCOLS))
@pytest.mark.usefixtures('has_no_containers_providers')
@pytest.mark.polarion('CMP-10586')
def test_add_hawkular_provider_ssl(provider, default_sec_protocols,
                                   hawkular_sec_protocols, soft_assert):
    """This test checks adding container providers  with 3 different security protocols:
    SSL trusting custom CA, SSL without validation and SSL
    The test checks the Default Endpoint as well as the Hawkular Endpoint
        """
    navigate_to(ContainersProvider, 'Add')
    fill(provider.properties_form, form_data(provider, default_sec_protocol=default_sec_protocols,
                                             hawkular_sec_protocol=hawkular_sec_protocols,
                                             with_hawkular=True))
    for cred in provider.credentials:
        try:
            fill(provider.credentials[cred].form, provider.credentials[cred], validate=True)
            provider._submit(False, provider.add_provider_button)
            flash.assert_message_contain('Containers Providers "' + provider.name + '" was saved')
        except:
            # The refresh is a workaround for
            # https://github.com/ManageIQ/integration_tests/issues/4478
            sel.refresh()
            soft_assert(False, provider.name + ' wasn\'t added successfully using ' +
                        default_sec_protocols + ' and ' +
                        hawkular_sec_protocols + ' hawkular security protocol')


def form_data(provider, default_sec_protocol, hawkular_sec_protocol=None, with_hawkular=False):
    name_text = provider.name
    type_select = 'OpenShift Container Platform'
    hostname_text = str(provider.hostname)
    hawkular_hostname = str(provider.hawkular_hostname)
    hostname_port = provider.port
    hawkular_api_port = provider.hawkular_api_port
    zone_select = 'default'
    default_ca_certificate = get_certificate(provider, sec_protocol=default_sec_protocol,
                                             cert_source=hostname_text)
    hawkular_ca_certificate = get_certificate(provider, sec_protocol=hawkular_sec_protocol,
                                              cert_source=hawkular_hostname)
    if with_hawkular:
        return {'name_text': name_text,
                'type_select': type_select,
                'hostname_text': hostname_text,
                'port_text': hostname_port,
                'trusted_ca_certificates': default_ca_certificate,
                'sec_protocol': default_sec_protocol,
                'zone_select': zone_select,
                'hawkular_hostname': hawkular_hostname,
                'hawkular_api_port': hawkular_api_port,
                'hawkular_sec_protocol': hawkular_sec_protocol,
                'hawkular_ca_certificates': hawkular_ca_certificate,
                }
    else:
        return {'name_text': name_text,
                'type_select': type_select,
                'hostname_text': hostname_text,
                'port_text': hostname_port,
                'trusted_ca_certificates': default_ca_certificate,
                'sec_protocol': default_sec_protocol,
                'zone_select': zone_select,
                }
