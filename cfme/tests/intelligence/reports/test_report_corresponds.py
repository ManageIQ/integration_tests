# -*- coding: utf-8 -*-
import pytest

from cfme.intelligence.reports.reports import CustomReport
from utils import version
from utils.providers import provider_factory_by_name
from utils.randomness import generate_random_string, pick


@pytest.yield_fixture(scope="function")
def report_vms():
    report = CustomReport(
        menu_name=generate_random_string(),
        title=generate_random_string(),
        base_report_on="Virtual Machines",
        report_fields=[
            version.pick({
                version.LOWEST: "Provider : Name",
                "5.3": "Cloud/Infrastructure Provider : Name",
            }),
            "Cluster : Name",
            "Datastore : Name",
            "Hardware : Number of CPUs",
            "Hardware : RAM",
            "Host : Name",
            "Name",
        ]
    )
    report.create()
    report.queue(wait_for_finish=True)
    yield pick(
        filter(
            lambda i: len(i[
                version.pick({
                    version.LOWEST: "Provider : Name",
                    "5.3": "Cloud/Infrastructure Provider Name",
                })
            ].strip()) > 0,
            list(report.get_saved_reports()[0].data.rows)), 2)
    report.delete()


def test_custom_vm_report(soft_assert, report_vms):
    for row in report_vms:
        provider_name = row[version.pick({
            version.LOWEST: "Provider : Name",
            "5.3": "Cloud/Infrastructure Provider Name",
        })]
        provider = provider_factory_by_name(provider_name)
        provider_hosts = provider.list_host()
        provider_datastores = provider.list_datastore()
        provider_clusters = provider.list_cluster()
        soft_assert(provider.does_vm_exist(row["Name"]), "VM {} does not exist in {}!".format(
            row["Name"], provider_name
        ))
        # We do these `if` checks because sometimes the field is not specified
        # TODO: Figure out if it is an error or not??
        if row["Cluster Name"]:
            soft_assert(
                row["Cluster Name"] in provider_clusters,
                "Cluster {} not found in {}!".format(row["Cluster Name"], str(provider_clusters))
            )
        if row["Datastore Name"]:
            soft_assert(
                row["Datastore Name"] in provider_datastores,
                "Datastore {} not found in {}!".format(
                    row["Datastore Name"], str(provider_datastores))
            )
        # Because of mixing long and short host names, we have to use both-directional `in` op.
        if row["Host Name"]:
            for host in provider_hosts:
                if row["Host Name"] in host or host in row["Host Name"]:
                    break
            else:
                soft_assert(
                    False,
                    "Host {} not found in {}!".format(row["Host Name"], str(provider_hosts))
                )
