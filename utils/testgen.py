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

from cfme.common.provider import BaseProvider
from cfme.infrastructure.config_management import get_config_manager_from_config
from cfme.infrastructure.pxe import get_pxe_server_from_config
from cfme.roles import group_data
from utils.conf import cfme_data
from utils.log import logger
from utils.providers import ProviderFilter, list_providers


def providers_by_class(metafunc, classes, required_fields=None):
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
        pytest_generate_tests = testgen.parametrize(testgen.providers_by_class, [GCEProvider],
            scope='module')
    """
    pf = ProviderFilter(classes=classes, required_fields=required_fields)
    return providers(metafunc, filters=[pf])


def generate(*args, **kwargs):
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
    gen_func = kwargs.pop('gen_func', providers_by_class)

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
        try:
            # hack to pass trough in case of a failed param_check
            # where it sets a custom message
            metafunc.function.uncollect
        except AttributeError:
            pytest.mark.uncollect(
                reason="provider was not parametrized did you forget --use-provider?"
            )(metafunc.function)


def fixture_filter(metafunc, argnames, argvalues):
    """Filter fixtures based on fixturenames in the function represented by ``metafunc``"""
    # Identify indeces of matches between argnames and fixturenames
    keep_index = [e[0] for e in enumerate(argnames) if e[1] in metafunc.fixturenames]

    # Keep items at indices in keep_index
    def f(l):
        return [e[1] for e in enumerate(l) if e[0] in keep_index]

    # Generate the new values
    argnames = f(argnames)
    argvalues = map(f, argvalues)
    return argnames, argvalues


def providers(metafunc, filters=None):
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

    for provider in list_providers(filters):
        argvalues.append([provider])
        # Use the provider key for idlist, helps with readable parametrized test output
        idlist.append(provider.key)
        # Add provider to argnames if missing
        if 'provider' in metafunc.fixturenames and 'provider' not in argnames:
            metafunc.function = pytest.mark.uses_testgen()(metafunc.function)
            argnames.append('provider')

    return argnames, argvalues, idlist


def all_providers(metafunc, **options):
    """ Returns providers of all types """
    return providers_by_class(metafunc, [BaseProvider], **options)


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
        pytest.mark.uncollect(reason=uncollect_msg)(metafunc.function)
