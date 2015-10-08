"""Test generation helpers

Intended to functionalize common tasks when working with the pytest_generate_tests hook.

When running a test, it is quite often the case that multiple parameters need to be passed
to a single test. An example of this would be the need to run a Provider Add test against
multiple providers. We will assume that the providers are stored in the yaml under a common
structure like so:

.. code-block:: yaml

    providers:
        prov_1:
            name: test
            ip: 10.0.0.1
        prov_2:
            name: test2
            ip: 10.0.0.2

Our test requires that we have a Provider Object and a management system object. Let's
assume a test prototype like so::

    test_provider_add(provider_obj, provider_mgmt_sys):

In this case we require the test to be run twice, once for prov_1 and then again for prov_2.
We are going to use the generate function to help us provide parameters to pass to
``pytest_generate_tests()``. ``pytest_generate_tests()`` requires three pieces of
information, ``argnames``, ``argvalues`` and an ``idlist``. ``argnames`` turns into the
names we use for fixtures. In this case, ``provider_obj`` and ``provider_mgmt_sys``.
``argvalues`` becomes the place where the ``provider_obj`` and ``provider_mgmt_sys``
items are stored. Each element of ``argvalues`` is a list containing a value for both
``provider_obj`` and ``provider_mgmt_sys``. Thus, taking an element from ``argvalues``
gives us the values to unpack to make up one test. An example is below, where we assume
that a provider object is obtained via the ``Provider`` class, and the ``mgmt_sys object``
is obtained via a ``MgmtSystem`` class.

===== =============== =================
~     provider_obj    provider_mgmt_sys
===== =============== =================
prov1 Provider(prov1) MgmtSystem(prov1)
prov2 Provider(prov2) MgmtSystem(prov2)
===== =============== =================

This is analogous to the following layout:

========= =============== ===============
~         argnames[0]     argnames[1]
========= =============== ===============
idlist[0] argvalues[0][0] argvalues[0][1]
idlist[1] argvalues[1][0] argvalues[1][1]
========= =============== ===============

This could be generated like so:

.. code-block:: python

    def gen_providers:

        argnames = ['provider_obj', 'provider_mgmt_sys']
        argvalues = []
        idlist = []

        for provider in yaml['providers']:
            idlist.append(provider)
            argvalues.append([
                Provider(yaml['providers'][provider]['name']),
                MgmtSystem(yaml['providers'][provider]['ip']))
            ])

        return argnames, argvalues, idlist

This is then used with pytest_generate_tests like so::

    pytest_generate_tests(gen_providers)

Additionally, py.test joins the values of ``idlist`` with dashes to generate a unique id for this
test, falling back to joining ``argnames`` with dashes if ``idlist`` is not set. This is the value
seen in square brackets in a test report on parametrized tests.

More information on ``parametrize`` can be found in pytest's documentation:

* https://pytest.org/latest/parametrize.html#_pytest.python.Metafunc.parametrize

"""
import pytest
import random

from collections import OrderedDict
from cfme.exceptions import UnknownProviderType
from cfme.infrastructure.pxe import get_pxe_server_from_config
from fixtures.prov_filter import filtered
from fixtures.templateloader import TEMPLATES
from cfme.roles import group_data
from utils import version
from utils.conf import cfme_data
from utils.log import logger
from utils.providers import (
    cloud_provider_type_map, infra_provider_type_map, provider_type_map, get_crud)


_version_operator_map = OrderedDict([('>=', lambda o, v: o >= v),
                                    ('<=', lambda o, v: o <= v),
                                    ('==', lambda o, v: o == v),
                                    ('!=', lambda o, v: o != v),
                                    ('>', lambda o, v: o > v),
                                    ('<', lambda o, v: o < v)])


def generate(gen_func, *args, **kwargs):
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
        pytest_generate_tests = testgen.generate(testgen.test_gen_func, arg1, arg2, kwarg1='a')

        # Concrete example using infra_providers and scope
        pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="module")

    Note:

        ``filter_unused`` is helpful, in that you don't have to accept all of the args in argnames
        in every test in the module. However, if all tests don't share one common parametrized
        argname, py.test may not have enough information to properly organize tests beyond the
        'function' scope. Thus, when parametrizing in the module scope, it's a good idea to include
        at least one common argname in every test signature to give pytest a clue in sorting tests.

    """
    # Pull out/default kwargs for this function and parametrize
    scope = kwargs.pop('scope', 'function')
    indirect = kwargs.pop('indirect', False)
    filter_unused = kwargs.pop('filter_unused', True)

    # If parametrize doesn't get you what you need, steal this and modify as needed
    def pytest_generate_tests(metafunc):
        argnames, argvalues, idlist = gen_func(metafunc, *args, **kwargs)
        # Filter out argnames that aren't requested on the metafunc test item, so not all tests
        # need all fixtures to run, and tests not using gen_func's fixtures aren't parametrized.
        if filter_unused:
            argnames, argvalues = fixture_filter(metafunc, argnames, argvalues)
        # See if we have to parametrize at all after filtering
        parametrize(metafunc, argnames, argvalues, indirect=indirect, ids=idlist, scope=scope)
    return pytest_generate_tests


def parametrize(metafunc, argnames, argvalues, *args, **kwargs):
    """parametrize wrapper that calls :py:func:`param_check`, and only parametrizes when needed

    This can be used in any place where conditional parametrization is used.

    """
    if param_check(metafunc, argnames, argvalues):
        metafunc.parametrize(argnames, argvalues, *args, **kwargs)


def fixture_filter(metafunc, argnames, argvalues):
    """Filter fixtures based on fixturenames in the function represented by ``metafunc``"""
    # Identify indeces of matches between argnames and fixturenames
    keep_index = [e[0] for e in enumerate(argnames) if e[1] in metafunc.fixturenames]

    # Keep items at indices in keep_index
    f = lambda l: [e[1] for e in enumerate(l) if e[0] in keep_index]

    # Generate the new values
    argnames = f(argnames)
    argvalues = map(f, argvalues)
    return argnames, argvalues


def provider_by_type(metafunc, provider_types, *fields, **options):
    """Get the values of the named field keys from ``cfme_data.get('management_systems', {})``

    Args:
        provider_types: A list of provider types to include. If None, all providers are considered
        *fields: Names of keys in an individual provider dict whose values will be returned when
            used as test function arguments
        **options: Explained below

    The ``**options`` available are defined below:

    * ``required_fields``: when fields passed are not present, skip them
    * ``choose_random``: choose a single provider from the list
    * ``template_location``: Specification where a required tempalte lies in the yaml, If not
      found in the provider, warning is printed and the test not collected. The spec
      is a tuple or list where each item is a key to the next field (str or int).

    The following test function arguments are special:

        ``provider``
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
                'type', 'name', 'credentials', 'provider', 'hosts'
            )
        metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')

        # Using the parametrize wrapper
        pytest_generate_tests = testgen.parametrize(testgen.provider_by_type, ['openstack', 'ec2'],
            'type', 'name', 'credentials', 'provider', 'hosts', scope='module')

    Note:

        Using the default 'function' scope, each test will be run individually for each provider
        before moving on to the next test. To group all tests related to single provider together,
        parametrize tests in the 'module' scope.

    Note:

        testgen for providers now requires the usage of test_flags for collection to work.
        Please visit http://cfme-tests.readthedocs.org/guides/documenting.html#documenting-tests
        for more details.

    """

    metafunc.function = pytest.mark.uses_testgen()(metafunc.function)

    argnames = list(fields)
    argvalues = []
    idlist = []
    template_location = options.pop("template_location", None)

    if 'provider' in metafunc.fixturenames and 'provider' not in argnames:
        argnames.append('provider')

    for provider, data in cfme_data.get('management_systems', {}).iteritems():

        # Check provider hasn't been filtered out with --use-provider
        if provider not in filtered:
            continue

        try:
            prov_obj = get_crud(provider)
        except UnknownProviderType:
            continue

        skip = False
        if provider_types is not None and prov_obj.type not in provider_types:
            # Skip unwanted types
            continue

        restricted_version = data.get('restricted_version', None)
        if restricted_version:
            logger.info('we found a restricted version')
            for op, comparator in _version_operator_map.items():
                # split string by op; if the split works, version won't be empty
                head, op, ver = restricted_version.partition(op)
                if not ver:  # This means that the operator was not found
                    continue
                if not comparator(version.current_version(), ver):
                    skip = True
                break
            else:
                raise Exception('Operator not found in {}'.format(restricted_version))

        # Test to see the test has meta data, if it does and that metadata contains
        # a test_flag kwarg, then check to make sure the provider contains that test_flag
        # if not, do not collect the provider for this particular test.

        # Obtain the tests flags
        meta = getattr(metafunc.function, 'meta', None)

        test_flags = getattr(meta, 'kwargs', {}) \
            .get('from_docs', {}).get('test_flag', '').split(',')
        if test_flags != ['']:
            test_flags = [flag.strip() for flag in test_flags]

            defined_flags = cfme_data.get('test_flags', '').split(',')
            defined_flags = [flag.strip() for flag in defined_flags]

            excluded_flags = data.get('excluded_test_flags', '').split(',')
            excluded_flags = [flag.strip() for flag in excluded_flags]

            allowed_flags = set(defined_flags) - set(excluded_flags)

            if set(test_flags) - allowed_flags:
                logger.info("Skipping Provider {} for test {} in module {} because "
                    "it does not have the right flags, "
                    "{} does not contain {}".format(provider,
                                                    metafunc.function.func_name,
                                                    metafunc.function.__module__,
                                                    list(allowed_flags),
                                                    list(set(test_flags) - allowed_flags)))
                continue

        try:
            if prov_obj.type == "scvmm" and version.current_version() < "5.3":
                # Ignore SCVMM on 5.2
                continue
        except Exception:  # No SSH connection
            continue

        # Get values for the requested fields, filling in with None for undefined fields
        data_values = {field: data.get(field, None) for field in fields}

        # Go through the values and handle the special 'data' name
        # report the undefined fields to the log
        for key in data_values.keys():
            if data_values[key] is None:
                if 'require_fields' not in options:
                    options['require_fields'] = True
                if options['require_fields']:
                    skip = True
                    logger.warning('Field "%s" not defined for provider "%s", skipping' %
                        (key, provider)
                    )
                else:
                    logger.debug('Field "%s" not defined for provider "%s", defaulting to None' %
                        (key, provider)
                    )
        if skip:
            continue

        # Check the template presence if requested
        if template_location is not None:
            o = data
            try:
                for field in template_location:
                    o = o[field]
            except (IndexError, KeyError):
                logger.info("Cannot apply {} to {} in the template specification, ignoring.".format(
                    repr(field), repr(o)))
            else:
                if not isinstance(o, basestring):
                    raise ValueError("{} is not a string! (for template)".format(repr(o)))
                templates = TEMPLATES.get(provider, None)
                if templates is not None:
                    if o not in templates:
                        logger.info(
                            "Wanted template {} on {} but it is not there!\n".format(o, provider))
                        # Skip collection of this one
                        continue

        values = []
        for arg in argnames:
            if arg == 'provider':
                metafunc.function = pytest.mark.provider_related()(metafunc.function)
                values.append(prov_obj)
            elif arg in data_values:
                values.append(data_values[arg])

        # skip when required field is not present and option['require_field'] == True
        argvalues.append(values)

        # Use the provider name for idlist, helps with readable parametrized test output
        idlist.append(provider)

    # pick a single provider if option['choose_random'] == True
    if 'choose_random' not in options:
        options['choose_random'] = False
    if idlist and options['choose_random']:
        single_index = idlist.index(random.choice(idlist))
        new_idlist = ['random_provider']
        new_argvalues = [argvalues[single_index]]
        logger.debug('Choosing random provider, "%s" selected, ' % (provider))
        return argnames, new_argvalues, new_idlist

    return argnames, argvalues, idlist


def cloud_providers(metafunc, *fields, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.cloud_provider_type_map`

    """
    return provider_by_type(metafunc, cloud_provider_type_map, *fields, **options)


def infra_providers(metafunc, *fields, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.infra_provider_type_map`

    """
    return provider_by_type(metafunc, infra_provider_type_map, *fields, **options)


def all_providers(metafunc, *fields, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.provider_type_map`

    """
    return provider_by_type(metafunc, provider_type_map, *fields, **options)


def auth_groups(metafunc, auth_mode):
    """Provides two test params based on the 'auth_modes' and 'group_roles' in cfme_data:

        ``group_name``:
            expected group name in provided by the backend specified in ``auth_mode``

        ``group_data``:
            list of nav destinations that should be visible as a member of ``group_name``

    Args:

        auth_mode: One of the auth_modes specified in ``cfme_data.get('auth_modes', {})``

    """
    argnames = ['group_name', 'group_data']
    argvalues = []
    idlist = []

    if auth_mode in cfme_data.get('auth_modes', {}):
        # If auth_modes exists, group_roles is assumed to exist as well
        gdata = group_data()
        for group in gdata:
            argvalues.append([group, sorted(gdata[group])])
            idlist.append(group)
    return argnames, argvalues, idlist


def pxe_servers(metafunc):
    """Provides pxe data based on the server_type

    Args:
        server_name: One of the server names to filter by, or 'all'.

    """
    argnames = ['pxe_name', 'pxe_server_crud']
    argvalues = []
    idlist = []

    data = cfme_data.get('pxe_servers', {})

    for pxe_server in data:
        argvalues.append([data[pxe_server]['name'],
                          get_pxe_server_from_config(pxe_server)])
        idlist.append(pxe_server)
    return argnames, argvalues, idlist


def param_check(metafunc, argnames, argvalues):
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
        skip_msg = 'Parametrization for %s yielded no values, marked for uncollection' % test_name
        logger.warning(skip_msg)

        # apply the mark
        pytest.mark.uncollect()(metafunc.function)
