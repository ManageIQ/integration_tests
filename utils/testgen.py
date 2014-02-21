"""Test generation helpers

Intended to functionalize common tasks when working with the pytest_generate_tests hook.

More detail on how the function returns ``argnames``, ``argvalues``, and ``idlist`` are used
can be found in pytest's parametrize documentation:

* https://pytest.org/latest/parametrize.html#_pytest.python.Metafunc.parametrize

"""

#import itertools

from cfme.infrastructure.provider import get_from_config as get_infra_provider
from cfme.cloud.provider import get_from_config as get_cloud_provider
from utils.conf import cfme_data
from utils.log import logger
from utils.providers import cloud_provider_type_map, infra_provider_type_map


def parametrize(gen_func, *args, **kwargs):
    """Functional handler for inline pytest_generate_tests definition

    Args:
        gen_func: Test generator function, expected to return argnames, argvalues, and an idlist
            suitable for use with pytest's parametrize method in pytest_generate_tests hooks
        indirect: Optional keyword argument. If seen, it will be removed from the kwargs
            passed to gen_func and used in the wrapped pytest parametrize call
        scope: Optional keyword argument. If seen, it will be removed from the kwargs
            passed to gen_func and used in the wrapped pytest parametrize call
        filter_unused: Optional keyword argument. If True (the default), parametrized tests will
            be inspected, and only argnames matching fixturenames will be used to parametrize the
            test. If seen, it will be removed from the kwargs passed to gen_func.
        *args: Additional positional arguments which will be passed to ``gen_func``
        **kwargs: Additional keyword arguments whill be passed to ``gen_func``

    Usage:

        # Abstract example:
        pytest_generate_tests = testgen.parametrize(testgen.test_gen_func, arg1, arg2, kwarg1='a')

        # Concrete example using infra_providers and scope
        pytest_generate_tests = testgen.parametrize(testgen.infra_providers, 'provider_crud',
            scope="module")

    Note:

        ``filter_unused`` is helpful, in that you don't have to accept all of the args in argnames
        in every test in the module. However, if all tests don't share one common parametrized
        argname, py.test may not have enough information to properly organize tests beyond the
        'function' scope. Thus, when parametrizing in the module scope, it's a good idea to include
        at least one common argname in every test signature to give pytest a clue in sorting tests.

    """
    # Pull out/default kwargs for this function and metafunc.parametrize
    scope = kwargs.pop('scope', 'function')
    indirect = kwargs.pop('indirect', False)
    filter_unused = kwargs.pop('filter_unused', True)

    # If parametrize doesn't get you what you need, steal this and modify as needed
    def pytest_generate_tests(metafunc):
        argnames, argvalues, idlist = gen_func(metafunc, *args, **kwargs)
        # Filter out argnames that aren't requested on the metafunc test item, so not all tests
        # need all fixtures to run, and tests not using gen_func's fixtures aren't parametrized.
        if filter_unused:
            argnames, argvalues = _fixture_filter(metafunc, argnames, argvalues)
        # See if we have to parametrize at all after filtering
        if argnames:
            metafunc.parametrize(argnames, argvalues, indirect=indirect, ids=idlist, scope=scope)
    return pytest_generate_tests


def _fixture_filter(metafunc, argnames, argvalues):
    # Identify indeces of matches between argnames and fixturenames
    keep_index = [e[0] for e in enumerate(argnames) if e[1] in metafunc.fixturenames]

    # Keep items at indices in keep_index
    fixture_filter = lambda l: [e[1] for e in enumerate(l) if e[0] in keep_index]

    # Generate the new values
    argnames = fixture_filter(argnames)
    argvalues = map(fixture_filter, argvalues)
    return argnames, argvalues


def provider_by_type(metafunc, provider_types, *fields):
    """Get the values of the named field keys from ``cfme_data['management_systems']``

    Args:
        provider_types: A list of provider types to include. If None, all providers are considered
        *fields: Names of keys in an individual provider dict whose values will be returned when
            used as test function arguments

    The following test function arguments are special:

        ``provider_data``
            the entire provider data dict from cfme_data.

        ``provider_key``
            the provider's key in ``cfme_data['management_systems']``

        ``provider_crud``
            the provider's CRUD object, either a :py:class:`cfme.cloud.provider.Provider`
            or a :py:class:`cfme.infrastructure.provider.Provider`

    Returns:
        An tuple of ``(argnames, argvalues, idlist)`` for use in a pytest_generate_tests hook, or
        with the :py:func:`parametrize` helper.

    Usage:

        # In the function itself
        def pytest_generate_tests(metafunc):
            argnames, argvalues, idlist = testgen.provider_by_type(
                ['openstack', 'ec2'],
                'type', 'name', 'credentials', 'provider_data', 'hosts'
            )
        metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')

        # Using the parametrize wrapper
        pytest_generate_tests = testgen.parametrize(testgen.provider_by_type, ['openstack', 'ec2'],
            'type', 'name', 'credentials', 'provider_data', 'hosts', scope='module')

    Note:

        Using the default 'function' scope, each test will be run individually for each provider
        before moving on to the next test. To group all tests related to single provider together,
        parametrize tests in the 'module' scope.

    """
    argnames = list(fields)
    argvalues = []
    idlist = []

    special_args = 'provider_key', 'provider_data', 'provider_crud'
    # Hook on special attrs if requested
    for argname in special_args:
        if argname in metafunc.fixturenames and argname not in argnames:
            argnames.append(argname)

    for provider, data in cfme_data['management_systems'].iteritems():
        if provider_types is not None and data['type'] not in provider_types:
            # Skip unwanted types
            continue

        # Use the provider name for idlist, helps with readable parametrized test output
        idlist.append(provider)

        # Get values for the requested fields, filling in with None for undefined fields
        values = [data.get(field, '') for field in fields]

        # Go through the values and handle the special 'data' name
        # report the undefined fields to the log
        for i, (field, value) in enumerate(zip(fields, values)):
            if value is None:
                logger.warn('Field "%s" not defined for provider "%s", defaulting to None' %
                    (field, provider)
                )

        if data['type'] in cloud_provider_type_map:
            crud = get_cloud_provider(provider)
        elif data['type'] in infra_provider_type_map:
            crud = get_infra_provider(provider)
        # else: wat? You deserve the NameError you're about to receive

        special_args_map = dict(zip(special_args, (provider, data, crud)))
        for arg in special_args:
            if arg in argnames:
                values.append(special_args_map[arg])
        argvalues.append(values)

    return argnames, argvalues, idlist


def cloud_providers(metafunc, *fields):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.cloud_provider_type_map`

    """
    return provider_by_type(metafunc, cloud_provider_type_map, *fields)


def infra_providers(metafunc, *fields):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.infra_provider_type_map`

    """
    return provider_by_type(metafunc, infra_provider_type_map, *fields)
