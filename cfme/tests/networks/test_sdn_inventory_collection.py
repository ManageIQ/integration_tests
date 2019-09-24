import fauxfactory
import pytest
from wait_for import wait_for

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.utils.appliance.implementations.ui import navigate_to

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

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/10h
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
def test_sdn_api_inventory_routers(provider, appliance):
    """Pulls the list of routers from the Provider API and from the appliance. Compare the 2
    results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory

    Bugzilla:
        1550605

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/10h
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

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/10h
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

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/10h
    """
    prov_sec_gp = sorted(provider.mgmt.list_security_group())
    cfme_sec_gp = sorted([sec.name for sec in appliance.collections.network_security_groups.all()])

    assert prov_sec_gp == cfme_sec_gp, 'Prov security groups list: {sec} different from '
    'cfme list: {cfme}'.format(sec=prov_sec_gp, cfme=cfme_sec_gp)


@pytest.mark.ignore_stream('5.11')  # Load Balancers are deprecated in 5.11
@pytest.mark.provider([EC2Provider, AzureProvider], override=True, scope='function')
def test_sdn_api_inventory_loadbalancers(provider, appliance):
    """Pulls the list of loadbalancers from the Provider API and from the appliance. Compare the 2
    results. If Similar, then test is successful

    Metadata:
        test_flag: sdn, inventory

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/10h
    """
    prov_load_balancers = sorted(provider.mgmt.list_load_balancer())
    cfme_load_balancers = sorted([lb.name for lb in appliance.collections.balancers.all()])

    assert prov_load_balancers == cfme_load_balancers, 'Provider balancer list: {prov} different '
    'from cfme list: {cfme}'.format(prov=prov_load_balancers, cfme=cfme_load_balancers)


@pytest.fixture
def secgroup_with_rule(provider):
    res_group = provider.data['provisioning']['resource_group']
    secgroup_name = 'secgroup_with_rule_{}'.format(fauxfactory.gen_alpha(8).lower())
    provider.mgmt.create_netsec_group(secgroup_name, res_group)
    provider.mgmt.create_netsec_group_port_allow(secgroup_name,
        'Tcp', '*', '*', 'Allow', 'Inbound', description='Allow port 22',
        source_port_range='*', destination_port_range='22', priority=100,
        name='Port_22_allow', resource_group=res_group)
    provider.refresh_provider_relationships()
    yield secgroup_name
    provider.mgmt.remove_netsec_group(secgroup_name, res_group)


@pytest.mark.provider([AzureProvider], override=True, scope='function')
def test_sdn_nsg_firewall_rules(provider, appliance, secgroup_with_rule):
    """ Pulls the list of firewall ports from Provider API and from appliance. Compare the 2
    results. If same, then test is successful.

    Metadata:
        test_flag: sdn, inventory

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        initialEstimate: 1/4h
    """

    # Navigate to network provider.
    prov_collection = appliance.collections.network_providers.filter({'provider': provider})
    network_provider = prov_collection.all()[0]
    network_provider.refresh_provider_relationships()
    wait_for(network_provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
    view = navigate_to(network_provider, 'Details')
    parent_name = view.entities.relationships.get_text_of("Parent Cloud Provider")
    assert parent_name == provider.name

    secgrp_collection = appliance.collections.network_security_groups
    secgroup = [i for i in secgrp_collection.all() if i.name == secgroup_with_rule][0]
    view = navigate_to(secgroup, 'Details')

    if appliance.version < '5.10':
        # The table has one header row. The first non-header row has column
        # names.
        assert 'Port' == view.entities.firewall_rules[1][3].text
        assert '22' == view.entities.firewall_rules[2][3].text
    else:
        # The table has two header rows. We cannot access the second one with
        # widgetastic. So let's hope the column of index 3 is the Port Range
        # column.
        assert '22' == view.entities.firewall_rules[1][3].text
