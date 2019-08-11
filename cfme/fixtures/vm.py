import fauxfactory
# -*- coding: utf-8 -*-
import re

import pytest
from polarion_collect import get_nodeid_full_path
from polarion_docstrings import parser as docparser
from wrapanapi import VmState

from cfme.cloud.provider.ec2 import EC2Provider
from cfme.exceptions import CFMEException
from cfme.utils import ports
from cfme.utils.generators import random_vm_name
from cfme.utils.net import net_check
from cfme.utils.wait import wait_for


DOCSTRING_CACHE = {}
TEST_PARAMS = re.compile(r"\[.*\]")


def get_parsed_docstring(request, nodeid, docstrings_cache):
    """Gets parsed docstring from cache."""
    if nodeid not in docstrings_cache:
        docstrings = docparser.get_docstrings_in_file(str(request.node.fspath.strpath))
        merged_docstrings = docparser.merge_docstrings(docstrings)
        docstrings_cache.update(merged_docstrings)
    return docstrings_cache[nodeid]


def _create_vm(request, template, provider, vm_name):
    if isinstance(request.node, pytest.Function):
        nodeid = TEST_PARAMS.sub("", get_nodeid_full_path(request.node))
        assignee = get_parsed_docstring(request, nodeid, DOCSTRING_CACHE).get('assignee', '')
    else:
        # Fetch list of tests in the module object
        test_list = [
            item
            for item in dir(request.module)
            if ('test_' in item[:5]) and not ('test_requirements' == item)
        ]
        # Find out assignee for each test in test_list
        assignee_list = list()
        for test in test_list:
            nodeid = f"{request.node.fspath.strpath}::{test}"
            try:
                assignee_list.append(get_parsed_docstring(request, nodeid, DOCSTRING_CACHE)
                    .get('assignee', ''))
            except KeyError:
                continue
        # If all tests have same assignee, set length will be 1, else set assignee='module'
        assignee = assignee_list[0] if len(set(assignee_list)) == 1 else 'module'

    vm_name = f"{vm_name}-{assignee}"

    collection = provider.appliance.provider_based_collection(provider)
    try:
        vm_obj = collection.instantiate(
            vm_name, provider,
            template_name=provider.data['templates'][template].name
        )
    except (KeyError, AttributeError):
        pytest.skip('No appropriate template was passed to the fixture.')
    vm_obj.create_on_provider(allow_skip="default")

    @request.addfinalizer
    def _cleanup():
        vm_obj.cleanup_on_provider()
        provider.refresh_provider_relationships()

    vm_obj.mgmt.ensure_state(VmState.RUNNING)

    # In order to have seamless SSH connection
    vm_ip, _ = wait_for(
        lambda: vm_obj.ip_address,
        num_sec=300,
        delay=5,
        fail_condition=None,
        message="wait for testing VM pingable IP address."
    )
    wait_for(
        net_check,
        func_args=[ports.SSH, vm_ip],
        func_kwargs={"force": True},
        num_sec=300,
        delay=5,
        message="testing VM's SSH available")
    if not vm_obj.exists:
        provider.refresh_provider_relationships()
        vm_obj.wait_to_appear()

    return vm_obj


def _get_vm_name(request):
    """Helper function to get vm name from test requirement mark.

    At first we try to get a requirement value from ``pytestmark`` module list. If it's missing we
    can try to look up it in the test function itself. There is one restriction for it. We cannot
    get the test function mark from module scoped fixtures.
    """
    req = [mark.args[0] for mark in request.module.pytestmark if mark.name == "requirement"]
    if not req and request.scope == "function":
        try:
            req = request.function.requirement.args
        except AttributeError:
            raise CFMEException("VM name can not be obtained")
    return random_vm_name(req[0])


@pytest.fixture(scope="module")
def create_vm_modscope(setup_provider_modscope, request, provider):
    if request.param:
        template_type = request.param
    else:
        pytest.error('Any appropriate Template was not passed to the fixture.')
    vm_name = _get_vm_name(request)
    return _create_vm(request, template_type, provider, vm_name)


@pytest.fixture(scope="function")
def create_vm(setup_provider, request, provider):
    if request.param:
        template_type = request.param
    else:
        pytest.error('Any appropriate Template was not passed to the fixture.')
    vm_name = _get_vm_name(request)
    return _create_vm(request, full_template, provider, vm_name)


def _create_instance(appliance, provider, template_name):
    instance = appliance.collections.cloud_instances.instantiate(random_vm_name('pwr-c'),
                                                                 provider,
                                                                 template_name)
    if not instance.exists_on_provider:
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    elif instance.provider.one_of(EC2Provider) and instance.mgmt.state == VmState.DELETED:
        instance.mgmt.rename('test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    return instance


@pytest.fixture(scope="function")
def testing_instance(appliance, provider, small_template, setup_provider):
    """ Fixture to provision instance on the provider
    """
    instance = _create_instance(appliance, provider, small_template.name)
    yield instance
    instance.cleanup_on_provider()
