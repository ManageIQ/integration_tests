# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from copy import copy

from cfme.cloud.provider import wait_for_provider_delete
from utils import letobj
from utils.log import logger


class TenantPlugin(object):
    REQUIRED_FIXTURES = ["tenant_test", "provider"]

    @pytest.mark.hookwrapper
    @pytest.mark.trylast
    def pytest_generate_tests(self, metafunc):
        yield
        if "tenant_test" not in metafunc.funcargnames:
            return

        # Check we have at least one openstack there
        for call in metafunc._calls:
            if (
                    "provider" in call.funcargs and call.funcargs["provider"].type == "openstack"):
                break
        else:
            return

        metadata = metafunc.function.meta
        tenants = metadata.kwargs['from_docs'].get("tenant", [])
        if isinstance(tenants, dict):
            tenants = tenants.keys()
        elif isinstance(tenants, basestring):
            tenants = [tenants]
        tenants = [None] + tenants

        params = []
        ids = []
        for tenant in tenants:
            params.append(pytest.mark.tenant((tenant,)))
            if tenant is None:
                ids.append("NOTENANT")
            else:
                ids.append("USETENANT={}".format(tenant))

        metafunc.parametrize(["tenant_test"], params, ids=ids)

    @pytest.mark.hookwrapper
    def pytest_pyfunc_call(self, pyfuncitem):
        # Ignore if no tenant fixture
        if "tenant_test" not in pyfuncitem.fixturenames:
            yield
            return
        # The check for all fixtures already happened in the generate_tests phase
        provider = pyfuncitem._request.getfuncargvalue('provider')
        tenant_test = pyfuncitem._request.getfuncargvalue('tenant_test')
        if tenant_test is None:
            # Do nothing, normal provider without specific tenant
            logger.info("{} got no tenant this time so ignoring".format(pyfuncitem.name))
            yield
            # And nothing special in the end
            return
        elif tenant_test == "random":
            logger.info("{} got random tenant this time".format(pyfuncitem.name))
            tenant_name = "test_{}".format(fauxfactory.gen_alpha())
            user_name = tenant_name
            user_pass = fauxfactory.gen_alpha(length=16)
            with provider.mgmt.with_tenant(tenant_name) as tenant_id:
                with provider.mgmt.with_user(
                        user_name, password=user_pass, tenant=tenant_id):
                    if provider.exists:
                        logger.info("Deleting provider {}".format(provider.key))
                        provider.delete(cancel=False)
                        wait_for_provider_delete(provider)
                        existed = True
                    else:
                        existed = False
                    updated_credentials = copy(provider.credentials)
                    updated_credentials.principal = user_name
                    updated_credentials.secret = user_pass
                    updated_credentials.verify_secret = user_pass
                    with letobj(provider, credentials=updated_credentials) as tenanted_provider:
                        logger.info(
                            "Creating provider {} with tenant {}, user {}".format(
                                provider.key, tenant_name, user_name))
                        tenanted_provider.create(validate_credentials=True)
                        try:
                            logger.info("Giving control back to test, now with tenanted provider.")
                            yield
                        finally:
                            if tenanted_provider.exists:
                                logger.info("Deleting tenanted provider after test.")
                                tenanted_provider.delete(cancel=False)
                                wait_for_provider_delete(provider)
                    if existed:
                        # To not disrupt things
                        provider.create(validate_credentials=True)
        else:
            # An existing tenant
            yield


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group.addoption('--tenant-testing',
                    action='store_true',
                    dest='tenant_testing_enabled',
                    default=False,
                    help='Enable testing of the multiple tenants. (default: %default)')


def pytest_configure(config):
    """ Event testing setup.

    Sets up and registers the EventListener plugin for py.test.
    If the testing is enabled, listener is started.
    """
    if config.getoption("tenant_testing_enabled"):
        plugin = TenantPlugin()
        assert config.pluginmanager.register(plugin, "tenant_testing")
