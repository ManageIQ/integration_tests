# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from pytest_polarion_collect.utils import get_parsed_docstring
from pytest_polarion_collect.utils import process_json_data
from wrapanapi import VmState

from cfme.cloud.provider.ec2 import EC2Provider
from cfme.exceptions import CFMEException
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger


def pytest_addoption(parser):
    parser.addoption(
        '--no-assignee-vm-name',
        action='store_true',
        default=False,
        help=(
            'If passed no-assignee-vm-name, vm names will not contain test_case assignee names.'
        )
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_finish(session):
    """This hook will call the process_json_data and cause _docstrings_cache
    to be populated so that we can access required information in the _create_vm."""
    if not session.config.getoption('--no-assignee-vm-name'):
        process_json_data(session, session.items)


def _create_vm(request, template, provider, vm_name):
    if not request.config.getoption('--no-assignee-vm-name'):
        if isinstance(request.node, pytest.Function):
            assignee = get_parsed_docstring(request.node,
                request.session._docstrings_cache).get('assignee', '')
        else:
            # Fetch list of tests in the module object
            test_list = [
                item
                for item in dir(request.module)
                if item.startswith('test_') and not ('test_requirements' == item)
            ]
            # Find out assignee for each test in test_list
            assignee_list = list()
            for test in test_list:
                nodeid = f'{request.node.fspath.strpath}::{test}'
                try:
                    assignee_list.append(request.session._docstrings_cache[nodeid]['assignee'])
                except KeyError:
                    continue
            # If all tests have same assignee, set length will be 1, else set assignee='module'
            assignee = assignee_list[0] if len(set(assignee_list)) == 1 else 'module'
        vm_name = f'{vm_name}-{assignee}'
    collection = provider.appliance.provider_based_collection(provider)
    try:
        vm_obj = collection.instantiate(
            vm_name, provider,
            template_name=provider.data['templates'][template].name
        )
    except (KeyError, AttributeError):
        pytest.skip('No appropriate template was passed to the fixture.')
    vm_obj.create_on_provider(allow_skip='default')

    @request.addfinalizer
    def _cleanup():
        vm_obj.cleanup_on_provider()
        provider.refresh_provider_relationships()

    vm_obj.mgmt.ensure_state(VmState.RUNNING)

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
    try:
        req = [mark.args[0] for mark in request.module.pytestmark if mark.name == "requirement"]
    except AttributeError:
        req = None
        logger.debug("Could not get the requirement from pytestmark")
    if not req and request.scope == "function":
        try:
            req = [mark.args for mark in request.function.pytestmark
            if mark.name == 'requirement'][0]
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
    return _create_vm(request, template_type, provider, vm_name)


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
