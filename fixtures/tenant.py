# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from _pytest.python import FixtureLookupError
from copy import copy

from utils.log import logger


TENANTED_SUFF = "-tenanted"


class TenantPlugin(object):
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
                ids.append(" | NO TENANT")
            elif tenant == "random":
                ids.append(" | RANDOM TENANT")
            else:
                ids.append(" | TENANT {}".format(tenant))

        metafunc.parametrize(["tenant_test"], params, ids=ids)

    @pytest.yield_fixture(scope="function")
    def tenanted_provider(self, request, provider):
        item = request._pyfuncitem
        tenanted_provider = copy(provider)
        tenanted_provider.name = provider.name + TENANTED_SUFF
        try:
            tenant_test = request.getfuncargvalue('tenant_test')
        except FixtureLookupError:
            yield None
            return

        if tenant_test == "random":
            logger.info("{} got random tenant this time".format(item.name))
            tenant_name = "test_{}".format(fauxfactory.gen_alpha())
            user_name = tenant_name
            user_pass = fauxfactory.gen_alpha(length=16)
            with provider.mgmt.with_tenant(tenant_name) as tenant_id:
                with provider.mgmt.with_user(
                        user_name, password=user_pass, tenant=tenant_id):
                    updated_credentials = copy(provider.credentials)
                    updated_credentials.principal = user_name
                    updated_credentials.secret = user_pass
                    updated_credentials.verify_secret = user_pass
                    tenanted_provider.credentials = updated_credentials
                    yield tenanted_provider
        else:
            # Other possibilities in-dev
            yield None


class DummyTenantPlugin(object):
    """This dummy plugin ensures the fixtures are available so things not fail."""
    @pytest.fixture(scope="function")
    def tenanted_provider(self, request, provider):
        return None


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
    else:
        plugin = DummyTenantPlugin()
    assert config.pluginmanager.register(plugin, "tenant_testing")
