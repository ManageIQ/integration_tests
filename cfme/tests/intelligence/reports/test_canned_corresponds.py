# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider import Provider, details_page
from cfme.intelligence.reports.reports import CannedSavedReport
from utils.net import ip_address, resolve_hostname
from utils.providers import get_mgmt_by_name, setup_a_provider as _setup_a_provider
from utils import version

provider_props = partial(details_page.infoblock.text, "Properties")


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider("infra")


@pytest.mark.tier(3)
def test_providers_summary(soft_assert, setup_a_provider):
    """Checks some informations about the provider. Does not check memory/frequency as there is
    presence of units and rounding."""
    path = ["Configuration Management", "Providers", "Providers Summary"]
    report = CannedSavedReport.new(path)
    for provider in report.data.rows:
        if any(ptype in provider["MS Type"] for ptype in {"ec2", "openstack"}):  # Skip cloud
            continue
        provider_fake_obj = Provider(name=provider["Name"])
        sel.force_navigate("infrastructure_provider", context={"provider": provider_fake_obj})
        hostname = version.pick({
            version.LOWEST: ("Hostname", "Hostname"),
            "5.5": ("Host Name", "Hostname")})
        soft_assert(
            provider_props(hostname[0]) == provider[hostname[1]],
            "Hostname does not match at {}".format(provider["Name"]))

        if version.current_version() < "5.4":
            # In 5.4, hostname and IP address are shared under Hostname (above)
            soft_assert(
                provider_props("IP Address") == provider["IP Address"],
                "IP Address does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("Aggregate Host CPU Cores") == provider["Total Number of Logical CPUs"],
            "Logical CPU count does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("Aggregate Host CPUs") == provider["Total Number of Physical CPUs"],
            "Physical CPU count does not match at {}".format(provider["Name"]))


@pytest.mark.tier(3)
def test_cluster_relationships(soft_assert, setup_a_provider):
    path = ["Relationships", "Virtual Machines, Folders, Clusters", "Cluster Relationships"]
    report = CannedSavedReport.new(path)
    for relation in report.data.rows:
        name = relation["Name"]
        provider_name = relation["Provider Name"]
        if not provider_name.strip():
            # If no provider name specified, ignore it
            continue
        provider = get_mgmt_by_name(provider_name)
        host_name = relation["Host Name"].strip()
        soft_assert(name in provider.list_cluster(), "Cluster {} not found in {}".format(
            name, provider_name
        ))
        if not host_name:
            continue  # No host name
        host_ip = resolve_hostname(host_name, force=True)
        if host_ip is None:
            # Don't check
            continue
        for host in provider.list_host():
            if ip_address.match(host) is None:
                host_is_ip = False
                ip_from_provider = resolve_hostname(host, force=True)
            else:
                host_is_ip = True
                ip_from_provider = host
            if not host_is_ip:
                # Strings first
                if host == host_name:
                    break
                elif host_name.startswith(host):
                    break
                elif ip_from_provider is not None and ip_from_provider == host_ip:
                    break
            else:
                if host_ip == ip_from_provider:
                    break
        else:
            soft_assert(False, "Hostname {} not found in {}".format(host_name, provider_name))
