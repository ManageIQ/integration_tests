import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.provider([EC2Provider, AzureProvider, GCEProvider]),
    pytest.mark.usefixtures('setup_provider')
]


def test_sdn_api_inventory_networks(provider, appliance):
    """Pulls the list of networks from the Provider API and from the appliance. Compare the 2
    results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory
    """
    prov_networks = sorted(provider.mgmt.list_network())
    cfme_networks = sorted([nt.name for nt in appliance.collections.cloud_networks.all()])

    if provider.one_of(EC2Provider):
        # Ec2 API returns only the Id of the networks, so the alternative is to count the networks
        # instead of checking there names. Less accurate, but Better than nothing...
        assert len(cfme_networks) == len(prov_networks), 'There is NOT the same amount of networks'
        'in CFME than on EC2: {prov} {cfme}'.format(prov=prov_networks, cfme=cfme_networks)
    else:
        assert cfme_networks == prov_networks, 'Prov networks list: {networks} different from '
        'cfme list: {cfme}'.format(networks=prov_networks, cfme=cfme_networks)


@pytest.mark.provider([AzureProvider, EC2Provider], override=True, scope='function')
@pytest.mark.meta(blockers=[BZ(1550605, forced_streams=["5.9", "5.8"],
                  unblock=lambda provider: not provider.one_of(AzureProvider))])
@pytest.mark.uncollectif(lambda provider, appliance: provider.one_of(EC2Provider) and
                         appliance.version < "5.9", reason='RFE for 5.9')
def test_sdn_api_inventory_routers(provider, appliance):
    """Pulls the list of routers from the Provider API and from the appliance. Compare the 2
    results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory
    """
    prov_routers = sorted(provider.mgmt.list_router())
    cfme_routers = sorted([rt.name for rt in appliance.collections.network_routers.all()])

    assert cfme_routers == prov_routers, 'Prov routers list: {router} different from cfme list: '
    '{cfme}'.format(router=prov_routers, cfme=cfme_routers)


def test_sdn_api_inventory_subnets(provider, appliance):
    """Pulls the list of subnets from the Provider API and from the appliance. Compare the 2
    results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory
    """
    prov_subnets = []
    cfme_subnets = [sb.name for sb in appliance.collections.network_subnets.all()]
    if provider.one_of(AzureProvider):
        # Because azure is the only provider which return a dict. The same might be done in
        # Wrapanapi for all providers.
        for sbn in provider.mgmt.list_subnet().values():
            prov_subnets.extend(sbn)
    else:
        prov_subnets = provider.mgmt.list_subnet()

    assert sorted(cfme_subnets) == sorted(prov_subnets), 'Prov subnets list: {sub} '
    'different from cfme list: {cfme}'.format(sub=prov_subnets, cfme=cfme_subnets)


@pytest.mark.provider([EC2Provider, AzureProvider], override=True, scope='function')
def test_sdn_api_inventory_security_groups(provider, appliance):
    """Pulls the list of security groups from the Provider API and from the appliance. Compare
    the 2 results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory
    """
    prov_sec_gp = sorted(provider.mgmt.list_security_group())
    cfme_sec_gp = sorted([sec.name for sec in appliance.collections.network_security_groups.all()])

    assert prov_sec_gp == cfme_sec_gp, 'Prov security groups list: {sec} different from '
    'cfme list: {cfme}'.format(sec=prov_sec_gp, cfme=cfme_sec_gp)


@pytest.mark.provider([EC2Provider, AzureProvider], override=True, scope='function')
def test_sdn_api_inventory_loadbalancers(provider, appliance):
    """Pulls the list of loadbalancers from the Provider API and from the appliance. Compare the 2
    results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory
    """
    prov_load_balancers = sorted(provider.mgmt.list_load_balancer())
    cfme_load_balancers = sorted([lb.name for lb in appliance.collections.balancers.all()])

    assert prov_load_balancers == cfme_load_balancers, 'Provider balancer list: {prov} different '
    'from cfme list: {cfme}'.format(prov=prov_load_balancers, cfme=cfme_load_balancers)
