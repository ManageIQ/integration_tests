# -*- coding: utf-8 -*-
import pytest
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider import Provider, details_page
from cfme.intelligence.reports.reports import CannedSavedReport
from utils.providers import provider_factory_by_name, setup_a_provider as _setup_a_provider

provider_props = partial(details_page.infoblock.text, "Properties")


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider("infra")


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
        soft_assert(
            provider_props("Hostname") == provider["Hostname"],
            "Hostname does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("IP Address") == provider["IP Address"],
            "IP Address does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("Aggregate Host CPU Cores") == provider["Total Number of Logical CPUs"],
            "Logical CPU count does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("Aggregate Host CPUs") == provider["Total Number of Physical CPUs"],
            "Physical CPU count does not match at {}".format(provider["Name"]))


def test_cluster_relationships(soft_assert, setup_a_provider):
    path = ["Relationships", "Virtual Machines, Folders, Clusters", "Cluster Relationships"]
    report = CannedSavedReport.new(path)
    for relation in report.data.rows:
        name = relation["Name"]
        provider_name = relation["Provider Name"]
        provider = provider_factory_by_name(provider_name)
        host_name = relation["Host Name"]
        soft_assert(name in provider.list_cluster(), "Cluster {} not found in {}".format(
            name, provider_name
        ))
        for host in provider.list_host():
            if host_name in host or host in host_name:  # Tends to get truncated and so
                break
        else:
            soft_assert(False, "Hostname {} not found in {}".format(host_name, provider_name))
