"""Validate resource (usage and allocation) values and costs in chargeback reports.

For a provider such as VMware that supports C&U, a chargeback report will show costs for both
resource usage and resource allocation.

For a provider such as SCVMM that doesn't support C&U, chargeback reports will show costs for
resource allocation only.
"""
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.fixtures.candu import RESOURCES
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.providers import ProviderFilter


cloud_and_infra = ProviderFilter(classes=[CloudProvider, InfraProvider],
                                 required_fields=[(['cap_and_util', 'test_chargeback'], True)])
not_scvmm = ProviderFilter(classes=[SCVMMProvider], inverted=True)  # SCVMM doesn't support C&U
not_cloud = ProviderFilter(classes=[CloudProvider], inverted=True)
not_gce = ProviderFilter(classes=[GCEProvider], inverted=True)

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers, filters=[cloud_and_infra, not_scvmm], scope='module'),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
]


# TODO: Parametrize provider marker.
@pytest.mark.parametrize('cost', [r.cost_name for r in RESOURCES])
def test_validate_chargeback_cost(chargeback_costs_parsed, chargeback_report_parsed, cost):
    """Validate the costs in a chargeback report.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    assert chargeback_costs_parsed[cost] == chargeback_report_parsed[cost]


# TODO: Parametrize provider marker.
@pytest.mark.parametrize('resource', [r.name for r in RESOURCES])
def test_validate_chargeback_resource(resource_totals_parsed, chargeback_report_parsed, resource):
    """Validate the resource usage and allocation values in a chargeback report.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    assert resource_totals_parsed[resource] == chargeback_report_parsed[resource]


# Provider parametrization:
#
# default:
# pytest.mark.provider(gen_func=providers,
#                      filters=[cloud_and_infra, not_scvmm],
#                      scope='module'),
#
# cpu_used:
# @pytest.mark.provider(gen_func=providers,
#                       filters=[cloud_and_infra, not_scvmm, not_cloud],
#                       scope='module')
#
# memory_used:
# @pytest.mark.provider(gen_func=providers,
#                       filters=[cloud_and_infra, not_scvmm, not_gce],
#                       scope='module')
#
# network_used:    default
# disk_used:       default
# storage_used:    default
#
# cpu_alloc:
# @pytest.mark.provider(gen_func=providers,
#                       filters=[cloud_and_infra, not_scvmm, not_cloud],
#                       scope='module')
#
# memory_alloc:    default [what about gce? it's excluded for memory_used]
# storage_alloc:   default
