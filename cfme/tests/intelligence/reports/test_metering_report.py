"""Tests for metering reports.
All providers that support C&U support metering reports. SCVMM doesn't support C&U.
Metering reports display only resource usage / allocation values, not costs.
"""
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.providers import ProviderFilter

cloud_and_infra = ProviderFilter(classes=[CloudProvider, InfraProvider],
                                 required_fields=[(['cap_and_util', 'test_chargeback'], True)])
not_scvmm = ProviderFilter(classes=[SCVMMProvider], inverted=True)  # SCVMM doesn't support C&U
not_cloud = ProviderFilter(classes=[CloudProvider], inverted=True)
not_ec2_gce = ProviderFilter(classes=[GCEProvider, EC2Provider], inverted=True)

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers, filters=[cloud_and_infra, not_scvmm], scope='module'),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
]

# Allowed deviation between the reported value in the Metering report and the estimated value.
DEVIATION = 1


def compare_values(estimated_value, report_value):
    report_value = report_value.replace(',', '')
    return (estimated_value - DEVIATION <= float(report_value) <= estimated_value + DEVIATION)


def get_report_value(report, report_key):
    """The report parameter provided by the metering_report fixture is a list of dicts, e.g.,
    [{'VM Name': 'cu-24x7', 'Date Range': '12/03/2019', 'CPU Used': '2.75 GHz', ... },
     {'VM Name': 'cu-24x7', 'Date Range': 'cu-24x7', 'CPU Used': 'cu-24x7', ... },
     {'VM Name': 'Totals:', 'Date Range': '', 'CPU Used': '2.75 GHz', ... },
     {'VM Name': '', 'Date Range': '', 'CPU Used': '', ... },
     {'VM Name': 'All Rows', 'Date Range': 'All Rows', 'CPU Used': 'All Rows', ... },
     {'VM Name': 'Totals:', 'Date Range': '', 'CPU Used': '2.75 GHz', ... },
    ]

    In practice, with only one VM in the report, only the first dict will be used. If we extend
    functionality to include reports for multiple VMs, providers, etc., we will want to key on
    other identifiers as well. Currently we simply return the value associated with the given
    report_key. We do not check for KeyError exceptions here, because the fixture created
    the report with the required fields.
    """
    report_value = None
    for groups in report:
        if groups[report_key]:
            report_value = groups[report_key]
            break
    return report_value


# Tests to validate usage reported in the Metering report for various metrics.
# The usage reported in the report should be approximately equal to the
# usage estimated in the resource_usage fixture, therefore a small deviation is fine.
@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_cloud],
                      scope='module')
def test_validate_cpu_usage(resource_usage, metering_report):
    """Test to validate CPU usage. This metric is not collected for cloud providers.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    report_value = get_report_value(metering_report, 'CPU Used')
    estimated_value = resource_usage['cpu_used']
    if 'GHz' in report_value:
        estimated_value = estimated_value * 10**-3
    report_value = report_value.replace('MHz', '').replace('GHz', '')
    assert compare_values(estimated_value, report_value), ("Estimated CPU usage "
        f"{estimated_value} does not match reported value {report_value}.")


@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_ec2_gce],
                      scope='module')
def test_validate_memory_usage(resource_usage, metering_report):
    """Test to validate memory usage. This metric is not collected for GCE, EC2.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    report_value = get_report_value(metering_report, 'Memory Used')
    estimated_value = resource_usage['memory_used']
    if 'GB' in report_value:
        estimated_value = estimated_value * 2**-10
    report_value = report_value.replace('MB', '').replace('GB', '')
    assert compare_values(estimated_value, report_value), ("Estimated memory usage "
        f"{estimated_value} does not match reported value {report_value}.")


def test_validate_network_usage(resource_usage, metering_report):
    """Test to validate network usage.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    report_value = get_report_value(metering_report, 'Network I/O Used')
    estimated_value = resource_usage['network_used']
    report_value = report_value.replace('KBps', '')
    assert compare_values(estimated_value, report_value), ("Estimated network I/O usage "
        f"{estimated_value} does not match reported value {report_value}.")


def test_validate_disk_usage(resource_usage, metering_report):
    """Test to validate disk usage.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    report_value = get_report_value(metering_report, 'Disk I/O Used')
    estimated_value = resource_usage['disk_used']
    report_value = report_value.replace('KBps', '')
    assert compare_values(estimated_value, report_value), ("Estimated disk I/O usage "
        f"{estimated_value} does not match reported value {report_value}.")


def test_validate_storage_usage(resource_usage, metering_report):
    """Test to validate storage usage.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    report_value = get_report_value(metering_report, 'Storage Used')
    estimated_value = resource_usage['storage_used']
    report_value = report_value.replace('MB', '').replace('GB', '')
    assert compare_values(estimated_value, report_value), ("Estimated storage usage "
        f"{estimated_value} does not match reported value {report_value}.")
