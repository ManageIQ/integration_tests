""" Fixtures to set up providers

Used to ensure that we have a provider set up on the appliance before running a test.

There are two ways to request a setup provider depending on what kind of test we create:

1. Test parametrized by provider (test is run once per each matching provider)
   For parametrized tests, provider is delivered by testgen. Testgen ensures that the requested
   provider is available as the ``provider`` parameter. It doesn't set the provider up, however, as
   it will only provide you with the appropriate provider CRUD object.
   To get the provider set up, we need to add one of the following fixtures to parameters as well:
   - ``setup_provider``
   - ``setup_provider_modscope``
   - ``setup_provider_clsscope``
   - ``setup_provider_funcscope`` (same as ``setup_provider``)

   This ensures that whatever is currently hiding under the ``provider`` parameter will be set up.

2. Test not parametrized by provider (test is run once and we just need some provider available)
   In this case, we don't really care about what sort of a provider we have available. Usually,
   we just want something to fill the UI with data so that we can test our provider non-specific
   functionality. For that, we can leverage one of the following fixtures:
   - ``infra_provider``
   - ``cloud_provider``
   - ``middleware_provider``
   - ``containers_provider``
   - ...and others

   If these don't really fit your needs, you can implement your own module-local ``a_provider``
   fixture using ``setup_one_by_class_or_skip`` or more adjustable ``setup_one_or_skip``.
   These functions do exactly what their names suggest - they setup one of the providers fitting
   given parameters or skip the test. All of these fixtures are (and should be) function scoped.
   Please keep that in mind when creating your module-local substitutes.

If setting up a provider fails, the issue is logged and an internal counter is incremented
as a result. If this counter reaches a predefined number of failures (see ``SETUP_FAIL_LIMIT``),
the failing provider will be added to the list of problematic providers and no further attempts
to set it up will be made.
"""
import pytest
import random
import six
from collections import defaultdict

from cfme.common.provider import BaseProvider, all_types
from fixtures.artifactor_plugin import fire_art_test_hook
from fixtures.pytest_store import store
from fixtures.templateloader import TEMPLATES
from cfme.utils.providers import ProviderFilter, list_providers
from cfme.utils.log import logger
from collections import Mapping

# List of problematic providers that will be ignored
_problematic_providers = set()
# Stores number of setup failures per provider
_setup_failures = defaultdict(lambda: 0)
# Once limit is reached, no furter attempts at setting up a given provider are made
SETUP_FAIL_LIMIT = 3


def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--provider-limit", action="store", default=1, type=int,
        help=(
            "Number of providers allowed to coexist on appliance. 0 means no limit. "
            "Use 1 or 2 when running on a single appliance, depending on HW configuration."))


def _artifactor_skip_providers(request, providers, skip_msg):
    skip_data = {
        'type': 'provider',
        'reason': ', '.join(p.key for p in providers),
    }
    fire_art_test_hook(request.node, 'skip_test', skip_data=skip_data)
    pytest.skip(skip_msg)


def _setup_provider_verbose(request, provider, appliance=None):
    if appliance is None:
        appliance = store.current_appliance
    try:
        if request.config.option.provider_limit > 0:
            existing_providers = [
                p for p in appliance.managed_known_providers if p.key != provider.key]
            random.shuffle(existing_providers)
            maximum_current_providers = request.config.option.provider_limit - 1
            if len(existing_providers) > maximum_current_providers:
                providers_to_remove = existing_providers[maximum_current_providers:]
                store.terminalreporter.write_line(
                    'Removing extra providers: {}'.format(', '.join(
                        [p.key for p in providers_to_remove])))
                for p in providers_to_remove:
                    logger.info('removing provider %r', p.key)
                    p.delete(cancel=False)
                # Decoupled wait for better performance
                for p in providers_to_remove:
                    logger.info('waiting for provider %r to disappear', p.key)
                    p.wait_for_delete()
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


def setup_or_skip(request, provider):
    """ Sets up given provider or skips the test

    Note:
        If a provider fails to setup SETUP_FAIL_LIMIT times, it will be added to the list
        of problematic providers and won't be used by any test until the end of the test run.
    """
    if provider in _problematic_providers:
        skip_msg = "Provider {} had been marked as problematic".format(provider.key)
        _artifactor_skip_providers(request, [provider], skip_msg)

    if not _setup_provider_verbose(request, provider):
        _artifactor_skip_providers(
            request, [provider], "Unable to setup provider {}".format(provider.key))


def setup_one_or_skip(request, filters=None, use_global_filters=True):
    """ Sets up one of matching providers or skips the test

    Args:
        filters: List of :py:class:`ProviderFilter` or None
        request: Needed for logging a potential skip correctly in artifactor
        use_global_filters: Will apply global filters as well if `True`, will not otherwise
    """

    filters = filters or []
    providers = list_providers(filters=filters, use_global_filters=use_global_filters)

    # All providers filtered out?
    if not providers:
        global_providers = list_providers(filters=None, use_global_filters=use_global_filters)
        if not global_providers:
            # This can also mean that there simply are no providers in the yamls!
            pytest.skip("No provider matching global filters found")
        else:
            pytest.skip("No provider matching test-specific filters found")

    # Are all providers marked as problematic?
    if _problematic_providers.issuperset(providers):
        skip_msg = "All providers marked as problematic: {}".format([p.key for p in providers])
        _artifactor_skip_providers(request, providers, skip_msg)

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
        if _setup_provider_verbose(request, provider):
            return provider

    skip_msg = "Failed to set up any matching providers: {}", [p.key for p in providers]
    _artifactor_skip_providers(request, non_existing, skip_msg)


def setup_one_by_class_or_skip(request, prov_class, use_global_filters=True):
    pf = ProviderFilter(classes=[prov_class])
    return setup_one_or_skip(request, filters=[pf], use_global_filters=use_global_filters)


def _generate_provider_fixtures():
    """ Generate provider setup and clear fixtures based on what classes are available

    This will make fixtures like "cloud_provider" and "has_no_cloud_providers" available to tests.
    """
    for prov_type, prov_class in all_types().iteritems():
        def gen_setup_provider(prov_class):
            @pytest.fixture(scope='function')
            def _setup_provider(request):
                """ Sets up one of the matching providers """
                return setup_one_by_class_or_skip(request, prov_class)
            return _setup_provider
        fn_name = '{}_provider'.format(prov_type)
        globals()[fn_name] = gen_setup_provider(prov_class)

        def gen_has_no_providers(prov_class):
            @pytest.fixture(scope='function')
            def _has_no_providers():
                """ Clears all providers of given class from the appliance """
                prov_class.clear_providers()
            return _has_no_providers
        fn_name = 'has_no_{}_providers'.format(prov_type)
        globals()[fn_name] = gen_has_no_providers(prov_class)


# Let's generate all the provider setup and clear fixtures within the scope of this module
_generate_provider_fixtures()


@pytest.fixture(scope="function")
def has_no_providers(request):
    BaseProvider.clear_providers()


@pytest.fixture(scope="module")
def has_no_providers_modscope(request):
    BaseProvider.clear_providers()


@pytest.fixture(scope="function")
def setup_only_one_provider(request, has_no_providers):
    return setup_one_or_skip(request)


@pytest.fixture(scope="function")
def setup_perf_provider(request, use_global_filters=True):
    pf = ProviderFilter(required_tags=['perf'])
    return setup_one_or_skip(request, filters=[pf], use_global_filters=use_global_filters)


# When we want to setup a provider provided by testgen
# ----------------------------------------------------
@pytest.fixture(scope='function')
def setup_provider(request, provider):
    """Function-scoped fixture to set up a provider"""
    return setup_or_skip(request, provider)


@pytest.fixture(scope='module')
def setup_provider_modscope(request, provider):
    """Module-scoped fixture to set up a provider"""
    return setup_or_skip(request, provider)


@pytest.fixture(scope='class')
def setup_provider_clsscope(request, provider):
    """Module-scoped fixture to set up a provider"""
    return setup_or_skip(request, provider)


@pytest.fixture
def setup_provider_funcscope(request, provider):
    """Function-scoped fixture to set up a provider"""
    return setup_or_skip(request, provider)
# -----------------------------------------------


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
    except AttributeError:
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
    return provider.data['provisioning']


@pytest.fixture(scope="function")
def console_template(provider):
    return _get_template(provider, 'console_template')


@pytest.fixture(scope="module")
def console_template_modscope(provider):
    return _get_template(provider, 'console_template')
