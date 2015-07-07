# -*- coding: utf-8 -*-
""" Tests of managing ESX hypervisors directly. If another direct ones will be supported, it should
not be difficult to extend the parametrizer.

"""
import pytest
import random

from cfme.infrastructure.provider import VMwareProvider, get_from_config, wait_for_provider_delete
from utils.conf import cfme_data, credentials
from utils.net import resolve_hostname
from utils.version import Version
from utils.wait import wait_for


def pytest_generate_tests(metafunc):
    arg_names = "provider", "provider_data", "original_provider_key"
    arg_values = []
    arg_ids = []
    for provider_key, provider in cfme_data.get("management_systems", {}).iteritems():
        if provider["type"] != "virtualcenter":
            continue
        hosts = provider.get("hosts", [])
        if not hosts:
            continue

        version = provider.get("version", None)
        if version is None:
            # No version, no test
            continue
        if Version(version) < "5.0":
            # Ignore lesser than 5
            continue

        host = random.choice(hosts)
        creds = credentials[host["credentials"]]
        ip_address = resolve_hostname(host["name"])
        cred = VMwareProvider.Credential(
            principal=creds["username"],
            secret=creds["password"],
            verify_secret=creds["password"]
        )
        # Mock provider data
        provider_data = {}
        provider_data.update(provider)
        provider_data["name"] = host["name"]
        provider_data["hostname"] = host["name"]
        provider_data["ipaddress"] = ip_address
        provider_data["credentials"] = host["credentials"]
        provider_data.pop("host_provisioning", None)
        provider_data["hosts"] = [host]
        provider_data["discovery_range"] = {}
        provider_data["discovery_range"]["start"] = ip_address
        provider_data["discovery_range"]["end"] = ip_address
        host_provider = VMwareProvider(
            name=host["name"],
            hostname=host["name"],
            ip_address=ip_address,
            credentials=cred,
            provider_data=provider_data,
        )
        arg_values.append([host_provider, provider_data, provider_key])
        arg_ids.append("{}/random_host".format(provider_key))
    metafunc.parametrize(arg_names, arg_values, ids=arg_ids, scope="module")


@pytest.yield_fixture(scope="module")
def setup_provider(provider, original_provider_key):
    original_provider = get_from_config(original_provider_key)
    if original_provider.exists:
        # Delete original provider's hosts first
        for host in original_provider.hosts:
            if host.exists:
                host.delete(cancel=False)
        # Get rid of the original provider, it would make a mess.
        original_provider.delete(cancel=False)
        wait_for_provider_delete(provider)
    provider.create()
    provider.refresh_provider_relationships()
    try:
        wait_for(
            lambda: any([
                provider.num_vm() > 0,
                provider.num_template() > 0,
                provider.num_datastore() > 0,
                provider.num_host() > 0,
            ]), num_sec=400, delay=5)
    except:
        provider.delete(cancel=False)
        raise
    yield
    for host in provider.hosts:
        if host.exists:
            host.delete(cancel=False)
    provider.delete(cancel=False)
    wait_for_provider_delete(provider)


def test_validate(provider, setup_provider, provider_data):
    """Since the provider (host) gets added in the fixture, nothing special has to happen here."""
    provider.validate(db=False)
