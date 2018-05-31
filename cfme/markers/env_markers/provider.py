import pytest
from distutils.version import LooseVersion

from cfme.markers.env import EnvironmentMarker
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter, list_providers
from cfme.utils.pytest_shortcuts import fixture_filter

ONE = 'one'
ALL = 'all'
LATEST = 'latest'
ONE_PER_VERSION = 'one_per_version'
ONE_PER_CATEGORY = 'one_per_category'
ONE_PER_TYPE = 'one_per_type'


def _param_check(metafunc, argnames, argvalues):
    """Helper function to check if parametrizing is necessary

    * If no argnames were specified, parametrization is unnecessary.
    * If argvalues were generated, parametrization is necessary.
    * If argnames were specified, but no values were generated, the test cannot run successfully,
      and will be uncollected using the :py:mod:`markers.uncollect` mark.

    See usage in :py:func:`parametrize`

    Args:
        metafunc: metafunc objects from pytest_generate_tests
        argnames: argnames list for use in metafunc.parametrize
        argvalues: argvalues list for use in metafunc.parametrize

    Returns:
        * ``True`` if this test should be parametrized
        * ``False`` if it shouldn't be parametrized
        * ``None`` if the test will be uncollected

    """
    assert isinstance(argvalues, list), "iterators break pytest expectations"
    # If no parametrized args were named, don't parametrize
    if not argnames:
        return False
    # If parametrized args were named and values were generated, parametrize
    elif any(argvalues):
        return True
    # If parametrized args were named, but no values were generated, mark this test to be
    # removed from the test collection. Otherwise, py.test will try to find values for the
    # items in argnames by looking in its fixture pool, which will almost certainly fail.
    else:
        # module and class are optional, but function isn't
        modname = getattr(metafunc.module, '__name__', None)
        classname = getattr(metafunc.cls, '__name__', None)
        funcname = metafunc.function.__name__

        test_name = '.'.join(filter(None, (modname, classname, funcname)))
        uncollect_msg = 'Parametrization for {} yielded no values,'\
            ' marked for uncollection'.format(test_name)
        logger.warning(uncollect_msg)

        # apply the mark
        pytest.mark.uncollect(reason=uncollect_msg)(metafunc.function)


def parametrize(metafunc, argnames, argvalues, *args, **kwargs):
    """parametrize wrapper that calls :py:func:`_param_check`, and only parametrizes when needed

    This can be used in any place where conditional parametrization is used.

    """
    kwargs.pop('selector')
    if _param_check(metafunc, argnames, argvalues):
        metafunc.parametrize(argnames, argvalues, *args, **kwargs)
    # if param check failed and the test was supposed to be parametrized around a provider
    elif 'provider' in metafunc.fixturenames:
        try:
            # hack to pass trough in case of a failed param_check
            # where it sets a custom message
            metafunc.function.uncollect
        except AttributeError:
            pytest.mark.uncollect(
                reason="provider was not parametrized did you forget --use-provider?"
            )(metafunc.function)


def providers(metafunc, filters=None, selector=ALL):
    """ Gets providers based on given (+ global) filters

    Note:
        Using the default 'function' scope, each test will be run individually for each provider
        before moving on to the next test. To group all tests related to single provider together,
        parametrize tests in the 'module' scope.

    Note:
        testgen for providers now requires the usage of test_flags for collection to work.
        Please visit http://cfme-tests.readthedocs.org/guides/documenting.html#documenting-tests
        for more details.
    """
    filters = filters or []
    argnames = []
    argvalues = []
    idlist = []

    # Obtains the test's flags in form of a ProviderFilter
    meta = getattr(metafunc.function, 'meta', None)
    test_flag_str = getattr(meta, 'kwargs', {}).get('from_docs', {}).get('test_flag')
    if test_flag_str:
        test_flags = test_flag_str.split(',')
        flags_filter = ProviderFilter(required_flags=test_flags)
        filters = filters + [flags_filter]

    potential_providers = list_providers(filters)

    if selector == ONE:
        if potential_providers:
            allowed_providers = [potential_providers[0]]
        else:
            allowed_providers = []
    elif selector == LATEST:
        allowed_providers = [sorted(
            potential_providers, key=lambda k:LooseVersion(
                str(k.data.get('version', 0))), reverse=True
        )[0]]
    elif selector == ONE_PER_TYPE:
        types = set()

        def add_prov(prov):
            types.add(prov.type)
            return prov

        allowed_providers = [
            add_prov(prov) for prov in potential_providers if prov.type not in types
        ]
    elif selector == ONE_PER_CATEGORY:
        categories = set()

        def add_prov(prov):
            categories.add(prov.category)
            return prov

        allowed_providers = [
            add_prov(prov) for prov in potential_providers if prov.category not in categories
        ]
    elif selector == ONE_PER_VERSION:
        versions = set()

        def add_prov(prov):
            versions.add(prov.data.get('version', 0))
            return prov

        allowed_providers = [
            add_prov(prov) for prov in potential_providers if prov.data.get(
                'version', 0) not in versions
        ]
    else:
        allowed_providers = potential_providers

    need_prov_keys = any(getattr(filt, 'type_name', None) is not None for filt in filter.classes)

    for provider in allowed_providers:
        argvalues.append([provider])
        # Use the provider key for idlist, helps with readable parametrized test output
        if selector == ONE:
            if need_prov_keys:
                idlist.append(provider.type_name)
            else:
                idlist.append(provider.category)
        elif selector == ONE_PER_CATEGORY:
            idlist.append(provider.category)
        elif selector == ONE_PER_TYPE:
            idlist.append(provider.type_name)
        else:
            idlist.append(provider.key)
        # Add provider to argnames if missing
        if 'provider' in metafunc.fixturenames and 'provider' not in argnames:
            metafunc.function = pytest.mark.uses_testgen()(metafunc.function)
            argnames.append('provider')
        if metafunc.config.getoption('sauce') or selector == ONE:
            break

    return argnames, argvalues, idlist


def providers_by_class(metafunc, classes, required_fields=None, selector=ALL):
    """ Gets providers by their class

    Args:
        metafunc: Passed in by pytest
        classes: List of classes to fetch
        required_fields: See :py:class:`cfme.utils.provider.ProviderFilter`

    Usage:
        # In the function itself
        def pytest_generate_tests(metafunc):
            argnames, argvalues, idlist = testgen.providers_by_class(
                [GCEProvider, AzureProvider], required_fields=['provisioning']
            )
        metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')

        # Using the parametrize wrapper
        pytest_generate_tests = testgen.parametrize([GCEProvider], scope='module')
    """
    pf = ProviderFilter(classes=classes, required_fields=required_fields)
    return providers(metafunc, filters=[pf], selector=selector)


class ProviderEnvironmentMarker(EnvironmentMarker):
    NAME = 'provider'

    def process_env_mark(self, metafunc):
        if hasattr(metafunc.function, self.NAME):
            mark = None
            for mark in getattr(metafunc.function, self.NAME):
                if 'override' in mark.kwargs.keys() and mark.kwargs['override']:
                    break
            else:
                if len(getattr(metafunc.function, self.NAME)._marks) >= 2:
                    raise Exception(
                        "You have an override provider without "
                        "specifying the override flag [{}]".format(metafunc.function.__name__)
                    )

            args = mark.args
            kwargs = mark.kwargs.copy()
            if 'override' in kwargs:
                kwargs.pop('override')
            scope = kwargs.pop('scope', 'function')
            indirect = kwargs.pop('indirect', False)
            filter_unused = kwargs.pop('filter_unused', True)
            selector = kwargs.pop('selector', ALL)
            gen_func = kwargs.pop('gen_func', providers_by_class)

            # If parametrize doesn't get you what you need, steal this and modify as needed
            kwargs.update({'selector': selector})
            argnames, argvalues, idlist = gen_func(metafunc, *args, **kwargs)
            # Filter out argnames that aren't requested on the metafunc test item, so not all tests
            # need all fixtures to run, and tests not using gen_func's fixtures aren't parametrized.
            if filter_unused:
                argnames, argvalues = fixture_filter(metafunc, argnames, argvalues)
                # See if we have to parametrize at all after filtering
            parametrize(
                metafunc, argnames, argvalues, indirect=indirect,
                ids=idlist, scope=scope, selector=selector
            )
