from collections.abc import Mapping

import pytest
from aenum import NamedConstant

from cfme.fixtures.templateloader import TEMPLATES
from cfme.utils.log import logger


# TODO restructure these to indirectly parametrize the name, and provide name constants here
# These are getting improperly imported and used as functions

class Templates(NamedConstant):
    DPORTGROUP_TEMPLATE = "dportgroup_template"
    DPORTGROUP_TEMPLATE_MODSCOPE = "dportgroup_template_modscope"
    DUAL_DISK_TEMPLATE = "dual_disk_template"
    DUAL_NETWORK_TEMPLATE = "dual_network_template"
    RHEL69_TEMPLATE = "rhel69_template"
    RHEL7_MINIMAL = "rhel7_minimal"
    RHEL7_MINIMAL_MODSCOPE = "rhel7_minimal_modscope"
    UBUNTU16_TEMPLATE = "ubuntu16_template"
    WIN7_TEMPLATE = "win7_template"
    WIN10_TEMPLATE = "win10_template"
    WIN2016_TEMPLATE = "win2016_template"
    WIN2012_TEMPLATE = "win2012_template"


@pytest.fixture(scope="function")
def template(template_location, provider):
    if template_location is not None:
        o = provider.data
        try:
            for field in template_location:
                o = o[field]
        except (IndexError, KeyError):
            logger.info("Cannot apply %r to %r in the template specification, ignoring.", field, o)
        else:
            if not isinstance(o, str):
                raise ValueError("{!r} is not a string! (for template)".format(o))
            if not TEMPLATES:
                # There is nothing in TEMPLATES, that means no trackerbot URL and no data pulled.
                # This should normally not constitute an issue so continue.
                return o
            templates = TEMPLATES.get(provider.key)
            if templates is not None:
                if o in templates:
                    return o
    logger.info("Wanted template %s on %s but it is not there!", o, provider.key)
    pytest.skip('Template not available')


def _get_template(provider, template_type_name):
    """Get the template name for the given template type
    YAML is expected to have structure with a templates section in the provider:
    provider:
        templates:
            small_template:
                name:
                creds:
            big_template:
                name:
                creds:
    Args:
        provider (obj): Provider object to lookup template on
        template_type_name (str): Template type to lookup (small_template, big_template, etc)
    Returns:
         (dict) template dictionary from the yaml, with name and creds key:value pairs
    """
    try:
        template_type = provider.data.templates.get(template_type_name)
    except (AttributeError, KeyError):
        logger.error("Wanted template %s on %s but it is not there!", template, provider.key)
        pytest.skip('No {} for provider {}'.format(template_type_name, provider.key))
    if not isinstance(template_type, Mapping):
        pytest.skip('Template mapping is incorrect, {} on provider {}'
                    .format(template_type_name, provider.key))
    return template_type


@pytest.fixture(scope="function")
def small_template(provider):
    return _get_template(provider, 'small_template')


@pytest.fixture(scope="module")
def small_template_modscope(provider):
    return _get_template(provider, 'small_template')


@pytest.fixture(scope="function")
def full_template(provider):
    return _get_template(provider, 'full_template')


@pytest.fixture(scope="module")
def full_template_modscope(provider):
    return _get_template(provider, 'full_template')


@pytest.fixture(scope="function")
def big_template(provider):
    return _get_template(provider, 'big_template')


@pytest.fixture(scope="module")
def big_template_modscope(provider):
    return _get_template(provider, 'big_template')


@pytest.fixture(scope="function")
def provisioning(provider):
    try:
        return provider.data['provisioning']
    except KeyError:
        logger.warning('Tests using the provisioning fixture '
                       'should include required_fields in their ProviderFilter marker')
        pytest.skip('Missing "provisioning" field in provider data')


@pytest.fixture(scope="function")
def console_template(provider):
    return _get_template(provider, 'console_template')


@pytest.fixture(scope="module")
def console_template_modscope(provider):
    return _get_template(provider, 'console_template')


@pytest.fixture(scope="function")
def ubuntu16_template(provider):
    return _get_template(provider, 'ubuntu16_template')


@pytest.fixture(scope="module")
def ubuntu16_template_modscope(provider):
    return _get_template(provider, 'ubuntu16_template')


@pytest.fixture(scope="function")
def rhel69_template(provider):
    return _get_template(provider, 'rhel69_template')


@pytest.fixture(scope="module")
def rhel69_template_modscope(provider):
    return _get_template(provider, 'rhel69_template')


@pytest.fixture(scope="function")
def rhel74_template(provider):
    return _get_template(provider, 'rhel74_template')


@pytest.fixture(scope="module")
def rhel74_template_modscope(provider):
    return _get_template(provider, 'rhel74_template')


@pytest.fixture(scope="function")
def win7_template(provider):
    return _get_template(provider, 'win7_template')


@pytest.fixture(scope="module")
def win7_template_modscope(provider):
    return _get_template(provider, 'win7_template')


@pytest.fixture(scope="function")
def win10_template(provider):
    return _get_template(provider, 'win10_template')


@pytest.fixture(scope="module")
def win10_template_modscope(provider):
    return _get_template(provider, 'win10_template')


@pytest.fixture(scope="function")
def win2012_template(provider):
    return _get_template(provider, 'win2012_template')


@pytest.fixture(scope="module")
def win2012_template_modscope(provider):
    return _get_template(provider, 'win2012_template')


@pytest.fixture(scope="function")
def win2016_template(provider):
    return _get_template(provider, 'win2016_template')


@pytest.fixture(scope="module")
def win2016_template_modscope(provider):
    return _get_template(provider, 'win2016_template')


@pytest.fixture(scope="function")
def dual_network_template(provider):
    return _get_template(provider, 'dual_network_template')


@pytest.fixture(scope="module")
def dual_network_template_modscope(provider):
    return _get_template(provider, 'dual_network_template')


@pytest.fixture(scope="function")
def dual_disk_template(provider):
    return _get_template(provider, 'dual_disk_template')


@pytest.fixture(scope="module")
def dual_disk_template_modscope(provider):
    return _get_template(provider, 'dual_disk_template')


@pytest.fixture(scope="function")
def dportgroup_template(provider):
    return _get_template(provider, 'dportgroup_template')


@pytest.fixture(scope="module")
def dportgroup_template_modscope(provider):
    return _get_template(provider, 'dportgroup_template')


@pytest.fixture(scope="function")
def rhel7_minimal(provider):
    return _get_template(provider, 'rhel7_minimal')


@pytest.fixture(scope="module")
def rhel7_minimal_modscope(provider):
    return _get_template(provider, 'rhel7_minimal')


@pytest.fixture(scope="function")
def s3_template(provider):
    return _get_template(provider, 's3_template')


@pytest.fixture(scope="module")
def s3_template_modscope(provider):
    return _get_template(provider, 's3_template')
