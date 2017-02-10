"""``setup_provider`` fixture

In test modules paramatrized with :py:func:`utils.testgen.providers_by_class` (should be
just about any module that needs a provider to run its tests), this fixture will set up
the single provider needed to run that test.

If the provider setup fails, this fixture will record that failure and skip future tests
using the provider.

"""
import pytest
import random
import six
from collections import defaultdict

from cfme.common.provider import BaseProvider, CloudInfraProvider
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.containers.provider import ContainersProvider
from cfme.middleware.provider import MiddlewareProvider
from fixtures.artifactor_plugin import art_client, get_test_idents
from fixtures.pytest_store import store
from fixtures.templateloader import TEMPLATES
from utils.providers import ProviderFilter, list_providers
from utils.log import logger
from collections import Mapping

# List of problematic providers that will be ignored
_problematic_providers = set()
# Stores number of setup failures per provider
_setup_failures = defaultdict(lambda: 0)
# Once limit is reached, no furter attempts at setting up a given provider are made
SETUP_FAIL_LIMIT = 3


def setup_one_or_skip(request, filters=None, use_global_filters=True):
    """ Sets up one of matching providers or skips the test

    Args:
        filters: List of :py:class:`ProviderFilter` or None
        request: Needed for logging a potential skip correctly in artifactor
        use_global_filters: Will apply global filters as well if `True`, will not otherwise
    """

    def _artifactor_skip_providers(providers, request):
        node = request.node
        name, location = get_test_idents(node)
        skip_data = {'type': 'provider', 'reason': [p.key for p in providers].join(', ')}
        art_client.fire_hook('skip_test', test_location=location, test_name=name,
            skip_data=skip_data)

    def _setup_provider(provider):
        """ Sets up given provider robustly

        Note:

            If a provider fails to setup SETUP_FAIL_LIMIT times, it will be added to the list
            of problematic providers and won't be used by any test until the end of the test run.
        """
        try:
            store.terminalreporter.write_line(
                "Trying to set up provider {}\n".format(provider.key), green=True)
            provider.setup()
            return True
        except Exception as e:
            logger.exception(e)
            _setup_failures[provider] += 1
            if _setup_failures[provider] >= SETUP_FAIL_LIMIT:
                _problematic_providers.add(provider)
                message = "Provider {} is now marked as problematic and won't be used again."\
                          " {}: {}".format(provider.key, type(e).__name__, str(e))
                logger.warning(message)
                store.terminalreporter.write_line(message + "\n", red=True)
            if provider.exists:
                # Remove it in order to not explode on next calls
                provider.delete(cancel=False)
                provider.wait_for_delete()
                message = "Provider {} was deleted because it failed to set up.".format(
                    provider.key)
                logger.warning(message)
                store.terminalreporter.write_line(message + "\n", red=True)
            return False

    filters = filters or []
    providers = list_providers(filters=filters, use_global_filters=use_global_filters)

    # All providers filtered out?
    if not providers:
        global_providers = list_providers(filters=None, use_global_filters=True)
        if not global_providers:
            # This can also mean that there simply are no providers in the yamls!
            pytest.skip("No provider matching global filters found")
        else:
            pytest.skip("No provider matching test-specific filters found")

    # Are all providers marked as problematic?
    if _problematic_providers.issuperset(providers):
        _artifactor_skip_providers(providers, request)
        pytest.skip("All providers marked as problematic: {}".format([p.key for p in providers]))

    # If there is a provider already set up matching the user's requirements, reuse it
    for provider in providers:
        if provider.exists:
            return provider

    # If we have more than one provider, we create two separate groups of providers, preferred
    # and not preferred, that we shuffle separately and then join together
    if len(providers) > 1:
        only_preferred_filter = ProviderFilter(required_fields=[("do_not_prefer", True)],
                                               inverted=True)
        preferred_providers = list_providers(
            filters=filters + [only_preferred_filter], use_global_filters=use_global_filters)
        not_preferred_providers = [p for p in providers if p not in preferred_providers]
        random.shuffle(preferred_providers)
        random.shuffle(not_preferred_providers)
        providers = preferred_providers + not_preferred_providers

    # Try to set up one of matching providers
    non_existing = [prov for prov in providers if not prov.exists]
    for provider in non_existing:
        if _setup_provider(provider):
            return provider

    _artifactor_skip_providers(non_existing, request)
    pytest.skip("Failed to set up any matching provider(s): {}", [p.key for p in providers])


def setup_one_by_class_or_skip(request, prov_class, use_global_filters=True):
    pf = ProviderFilter(classes=[prov_class])
    return setup_one_or_skip(request, filters=[pf], use_global_filters=use_global_filters)


@pytest.fixture(scope="module")
def core_provider(request):
    return setup_one_by_class_or_skip(request, CloudInfraProvider)


@pytest.fixture(scope="module")
def infra_provider(request):
    return setup_one_by_class_or_skip(request, InfraProvider)


@pytest.fixture(scope="module")
def cloud_provider(request):
    return setup_one_by_class_or_skip(request, CloudProvider)


@pytest.fixture(scope='module')
def setup_provider(request, provider):
    """Function-scoped fixture to set up a provider"""
    return setup_one_or_skip(request, filters=[ProviderFilter(keys=[provider.key])])


@pytest.fixture(scope='module')
def setup_provider_modscope(request, provider):
    """Module-scoped fixture to set up a provider"""
    return setup_one_or_skip(request, filters=[ProviderFilter(keys=[provider.key])])


@pytest.fixture(scope='class')
def setup_provider_clsscope(request, provider):
    """Module-scoped fixture to set up a provider"""
    return setup_one_or_skip(request, filters=[ProviderFilter(keys=[provider.key])])


@pytest.fixture
def setup_provider_funcscope(request, provider):
    """Function-scoped fixture to set up a provider

    Note:

        While there are cases where this is useful, provider fixtures should
        be module-scoped the majority of the time.

    """
    return setup_one_or_skip(request, filters=[ProviderFilter(keys=[provider.key])])


@pytest.fixture(scope="session")
def any_provider_session(request):
    BaseProvider.clear_providers()
    return setup_one_or_skip(request)


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
            if not isinstance(o, six.string_types):
                raise ValueError("{!r} is not a string! (for template)".format(o))
            if not TEMPLATES:
                # There is nothing in TEMPLATES, that means no trackerbot URL and no data pulled.
                # This should normally not constitute an issue so continue.
                return o
            templates = TEMPLATES.get(provider.key, None)
            if templates is not None:
                if o in templates:
                    return o
    logger.info("Wanted template %s on %s but it is not there!", o, provider.key)
    pytest.skip('Template not available')


def _get_template(provider, template_type_name):
    template = provider.data.get(template_type_name, None)
    if isinstance(template, Mapping):
        template_name = template.get("name", None)
    else:
        template_name = template
    if template_name:
        if not TEMPLATES:
            # Same as couple of lines above
            return template
        templates = TEMPLATES.get(provider.key, None)
        if templates and template_name in templates:
            return template
    else:
        pytest.skip('No {} for provider {}'.format(template_type_name, provider.key))
    logger.info("Wanted template %s on %s but it is not there!", template, provider.key)
    pytest.skip('Template not available')


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
    return provider.data['provisioning']


@pytest.fixture
def has_no_providers():
    """ Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers()


@pytest.fixture
def has_no_cloud_providers():
    """ Clears all cloud providers from an appliance

    This is a destructive fixture. It will clear all cloud managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers_by_class(CloudProvider, validate=True)


@pytest.fixture
def has_no_infra_providers():
    """ Clears all infrastructure providers from an appliance

    This is a destructive fixture. It will clear all infrastructure managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers_by_class(InfraProvider, validate=True)


@pytest.fixture
def has_no_containers_providers():
    """ Clears all containers providers from an appliance

    This is a destructive fixture. It will clear all container managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers_by_class(ContainersProvider, validate=True)


@pytest.fixture
def has_no_middleware_providers():
    """Clear all middleware providers."""
    BaseProvider.clear_providers_by_class(MiddlewareProvider, validate=True)
