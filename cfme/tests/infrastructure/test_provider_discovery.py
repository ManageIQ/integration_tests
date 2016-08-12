from __future__ import unicode_literals
import pytest
from itertools import combinations

from utils import testgen
from utils.providers import get_crud, clear_provider_by_type
from cfme.infrastructure.provider import discover
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider


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
    types = ['virtualcenter', 'rhevm', 'scvmm']
    argnames, argvalues, idlist = testgen.provider_by_type(
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


@pytest.yield_fixture(scope='function')
def delete_providers_after_test():
    yield
    clear_provider_by_type('infra')


@pytest.mark.tier(2)
@pytest.mark.usefixtures('has_no_infra_providers', 'delete_providers_after_test')
def test_discover_infra(providers_for_discover, start_ip, max_range):
    rhevm = False
    scvmm = False
    virtualcenter = False

    for i in providers_for_discover:
        if type(i) == RHEVMProvider:
                rhevm = True
        if type(i) == SCVMMProvider:
                scvmm = True
        if type(i) == VMwareProvider:
                virtualcenter = True

    discover(rhevm, virtualcenter, scvmm, False, start_ip, max_range)

    @pytest.wait_for(num_sec=count_timeout(start_ip, max_range), delay=5)
    def _wait_for_all_providers():
        for provider in providers_for_discover:
            if provider.key not in pytest.store.current_appliance.managed_providers:
                return False
        if len(pytest.store.current_appliance.managed_providers) != len(providers_for_discover):
            return False
        return True


def count_timeout(start_ip, max_range):
    count = int(max_range) - int(start_ip.rsplit('.', 1)[-1])
    result = count * 30
    if result < 300:   # At least 5mins always
        result = 300
    return result
