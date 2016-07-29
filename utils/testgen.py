
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
            test_vm: abc1
        prov_2:
            name: test2
            ip: 10.0.0.2
            test_vm: abc2
Our test requires that we have a Provider Object and as an example, the 'test_vm' field of the
object. Let's assume a test prototype like so::
    test_provider_add(provider_obj, test_vm):
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
~     provider_obj    test_vm
===== =============== =================
prov1 Provider(prov1) abc1
prov2 Provider(prov2) abc2
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
        argnames = ['provider_obj', 'test_vm']
        argvalues = []
        idlist = []
        for provider in yaml['providers']:
            idlist.append(provider)
            argvalues.append([
                Provider(yaml['providers'][provider]['name']),
                yaml['providers'][provider]['test_vm'])
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

from collections import OrderedDict
from cfme.exceptions import UnknownProviderType
from cfme.infrastructure.pxe import get_pxe_server_from_config
from fixtures.prov_filter import filtered
from cfme.roles import group_data
from utils import version
from utils.conf import cfme_data
from utils.log import logger
from utils.providers import get_crud
from cfme.infrastructure.config_management import get_config_manager_from_config

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
    # if param check failed and the test was supposed to be parametrized around a provider
    elif 'provider' in metafunc.fixturenames:
        pytest.mark.uncollect(metafunc.function)


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


def _uncollect_restricted_version(data, metafunc, required_fields):
    restricted_version = data.get('restricted_version', None)
    if restricted_version:
        logger.info('we found a restricted version')
        for op, comparator in _version_operator_map.items():
            # split string by op; if the split works, version won't be empty
            head, op, ver = restricted_version.partition(op)
            if not ver:  # This means that the operator was not found
                continue
            if not comparator(version.current_version(), ver):
                return True
            break
        else:
            raise Exception('Operator not found in {}'.format(restricted_version))
    return False


def _check_required_fields(data, metafunc, required_fields):
    if required_fields:
        for field_or_fields in required_fields:
            if isinstance(field_or_fields, tuple):
                field_ident, field_value = field_or_fields
            else:
                field_ident, field_value = field_or_fields, None
            if isinstance(field_ident, basestring):
                if field_ident not in data:
                    return True
                else:
                    if field_value:
                        if data[field_ident] != field_value:
                            return True
            else:
                o = data
                try:
                    for field in field_ident:
                        o = o[field]
                    if field_value:
                        if o != field_value:
                            return True
                except (IndexError, KeyError):
                    return True
    return False


def _uncollect_test_flags(data, metafunc, required_fields):
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
            logger.info("Uncollecting Provider %s for test %s in module %s because "
                "it does not have the right flags, "
                "%s does not contain %s",
                data['name'], metafunc.function.func_name, metafunc.function.__module__,
                list(allowed_flags), list(set(test_flags) - allowed_flags))
            return True
    return False


def _uncollect_since_version(data, metafunc, required_fields):
    try:
        if "since_version" in data:
            # Ignore providers that are not supported in this version yet
            if version.current_version() < data["since_version"]:
                return True
    except Exception:  # No SSH connection
        return True
    return False


def provider_by_type(metafunc, provider_types, required_fields=None):
    """Get the values of the named field keys from ``cfme_data.get('management_systems', {})``
    ``required_fields`` is special and can take many forms, it is used to ensure that
    yaml data is present for a particular key, or path of keys, and can even validate
    the values as long as they are not None.
    Args:
        provider_types: A list of provider types to include. If None, all providers are considered
    Returns:
        An tuple of ``(argnames, argvalues, idlist)`` for use in a pytest_generate_tests hook, or
        with the :py:func:`parametrize` helper.
    Usage:
        # In the function itself
        def pytest_generate_tests(metafunc):
            argnames, argvalues, idlist = testgen.provider_by_type(
                ['openstack', 'ec2'], required_fields=['provisioning']
            )
        metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')
        # Using the parametrize wrapper
        pytest_generate_tests = testgen.parametrize(testgen.provider_by_type, ['openstack', 'ec2'],
            scope='module')
        # Using required_fields
        # Ensures that ``provisioning`` exists as a yaml field
        testgen.provider_by_type(
            ['openstack', 'ec2'], required_fields=['provisioning']
        )
        # Ensures that ``provisioning`` exists as a yaml field and has another field in it called
        # ``host``
        testgen.provider_by_type(
            ['openstack', 'ec2'], required_fields=[['provisioning', 'host']]
        )
        # Ensures that ``powerctl`` exists as a yaml field and has a value 'True'
        testgen.provider_by_type(
            ['openstack', 'ec2'], required_fields=[('powerctl', True)]
        )
    Note:
        Using the default 'function' scope, each test will be run individually for each provider
        before moving on to the next test. To group all tests related to single provider together,
        parametrize tests in the 'module' scope.
    Note:
        testgen for providers now requires the usage of test_flags for collection to work.
        Please visit http://cfme-tests.readthedocs.org/guides/documenting.html#documenting-tests
        for more details.
    """

    argnames = []
    argvalues = []
    idlist = []

    for provider in cfme_data.get('management_systems', {}):

        # Check provider hasn't been filtered out with --use-provider
        if provider not in filtered:
            continue

        try:
            prov_obj = get_crud(provider)
        except UnknownProviderType:
            continue

        if not prov_obj:
            logger.debug("Whilst trying to create an object for %s we failed", provider)
            continue

        if provider_types is not None:
            if not(prov_obj.type_tclass in provider_types or prov_obj.type_name in provider_types):
                continue

        # Run through all the testgen uncollect fns
        uncollect = False
        uncollect_fns = [_uncollect_restricted_version, _check_required_fields,
            _uncollect_test_flags, _uncollect_since_version]
        for fn in uncollect_fns:
            if fn(prov_obj.data, metafunc, required_fields):
                uncollect = True
                break
        if uncollect:
            continue

        if 'provider' in metafunc.fixturenames and 'provider' not in argnames:
            metafunc.function = pytest.mark.uses_testgen()(metafunc.function)
            argnames.append('provider')

        # uncollect when required field is not present and option['require_field'] == True
        argvalues.append([prov_obj])

        # Use the provider name for idlist, helps with readable parametrized test output
        idlist.append(provider)

    return argnames, argvalues, idlist


def cloud_providers(metafunc, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.cloud_provider_type_map`
    """
    return provider_by_type(metafunc, 'cloud', **options)


def infra_providers(metafunc, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.infra_provider_type_map`
    """
    return provider_by_type(metafunc, 'infra', **options)


def container_providers(metafunc, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.container_provider_type_map`
    """
    return provider_by_type(metafunc, 'container', **options)


def middleware_providers(metafunc, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.container_provider_type_map`
    """
    return provider_by_type(metafunc, 'middleware', **options)


def all_providers(metafunc, **options):
    """Wrapper for :py:func:`provider_by_type` that pulls types from
    :py:attr:`utils.providers.provider_type_map`
    """
    return provider_by_type(metafunc, None, **options)


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
        for group in group_data:
            argvalues.append([group, sorted(group_data[group])])
            idlist.append(group)
    return argnames, argvalues, idlist


def config_managers(metafunc):
    """Provides config managers
    """
    argnames = ['config_manager_obj']
    argvalues = []
    idlist = []

    data = cfme_data.get('configuration_managers', {})

    for cfg_mgr_key in data:
        argvalues.append([get_config_manager_from_config(cfg_mgr_key)])
        idlist.append(cfg_mgr_key)
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
        uncollect_msg = 'Parametrization for {} yielded no values,'\
            ' marked for uncollection'.format(test_name)
        logger.warning(uncollect_msg)

        # apply the mark
        pytest.mark.uncollect()(metafunc.function)

    Contact GitHub API Training Shop Blog About

    © 2016 GitHub, Inc. Terms Privacy Security Status Help

