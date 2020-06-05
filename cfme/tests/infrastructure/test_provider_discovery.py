from itertools import combinations

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.providers import get_crud
from cfme.utils.wait import wait_for_decorator


pytestmark = [test_requirements.discovery]


def generate_signature(combination):
    return '-'.join([p.type for p in combination])


def find_neighbour_provider_combinations(providers, upto):
    neighbours = []
    combinations_seen = set()

    for count in range(1, upto + 1):
        for combination in combinations(providers, count):
            ip_prefix = '.'.join(combination[0].ip_address.split('.')[:3])
            if not all(provider.ip_address.startswith(ip_prefix) for provider in combination[1:]):
                continue
            # They are in one /24, which is good
            # Filter out duplicite provider types
            filtered_combination = []
            types_seen = set()
            for provider in combination:
                if provider.type in types_seen:
                    continue
                types_seen.add(provider.type)
                filtered_combination.append(provider)
            # We have ensured the provider types are unique - appearing only once
            combination = sorted(filtered_combination, key=lambda provider: provider.type)
            # Check if we already have such combination in place, if yes, skip this round
            combination_tuple = tuple(provider.type for provider in combination)
            if combination_tuple in combinations_seen:
                continue
            combinations_seen.add(combination_tuple)
            # Finally, add this parametrization in place
            neighbours.append(combination)

    return neighbours


def minmax_ip(providers):
    ips = sorted([tuple(map(int, provider.ip_address.split('.'))) for provider in providers])
    return '.'.join(map(str, ips[0])), str(ips[-1][-1])   # Last number of last IP


def pytest_generate_tests(metafunc):
    types = [VMwareProvider, RHEVMProvider, SCVMMProvider]
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, types)

    argnames = ['providers_for_discover', 'start_ip', 'max_range']
    new_id_list = []

    providers_complete = []
    providers_final = []

    for x in idlist:
        providers_complete.append(get_crud(x))

    provider_combinations = sorted(
        find_neighbour_provider_combinations(providers_complete, len(types)), key=len)
    signatures_seen = set()

    for prov_comb in provider_combinations:
        sig = generate_signature(prov_comb)
        if sig in signatures_seen:
            continue
        signatures_seen.add(sig)
        start_ip, max_range = minmax_ip(prov_comb)
        providers_final.append([prov_comb, start_ip, max_range])
        new_id_list.append(sig)

    testgen.parametrize(metafunc, argnames, providers_final, ids=new_id_list, scope="module")


@pytest.fixture(scope='function')
def delete_providers_after_test():
    yield
    InfraProvider.clear_providers()


@pytest.mark.tier(2)
def test_discover_infra(
    appliance,
    has_no_providers,
    providers_for_discover,
    start_ip,
    max_range,
    delete_providers_after_test,
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/16h
        upstream: yes
    """
    collection = appliance.collections.infra_providers
    for provider in providers_for_discover:
        collection.discover(provider, False, start_ip, max_range)

    @wait_for_decorator(num_sec=count_timeout(start_ip, max_range), delay=5)
    def _wait_for_all_providers():
        for provider in providers_for_discover:
            provider.browser.refresh()
            # When the provider is discovered, its name won't match what would be expected from
            # the crud objects generated from yaml data. The name in CFME will contain an IP
            # which should uniquely identify the resource
            if [name for name in provider.appliance.managed_provider_names
                    if provider.ip_address in name]:
                # provider IP matched an appliance provider
                continue
            else:
                return False
        else:
            # all provider IPs found in the provider names
            return True


def count_timeout(start_ip, max_range):
    count = int(max_range) - int(start_ip.rsplit('.', 1)[-1])
    result = count * 30
    if result < 300:   # At least 5mins always
        result = 300
    return result
