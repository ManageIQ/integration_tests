# -*- coding: utf-8 -*-
import operator
import pytest

from cfme.configure.tasks import is_host_analysis_finished
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.host import Host
from cfme.web_ui import InfoBlock, Quadicon, toolbar
from utils import conf, testgen
from utils.wait import wait_for


ROLE_MAPPING = {
    'compute': 'Compute',
    'controller': 'Controller',
}

OP_MAP = {
    '!=': operator.ne,
    '==': operator.eq,
    'in': operator.contains,
}


def pytest_generate_tests(metafunc):
    names, parametrizations, idlist = testgen.provider_by_type(
        metafunc, ['openstack-infra'], required_fields=['deployed_nodes'])

    provider_index = names.index('provider')
    # Add the new params
    for name in ['host_type', 'check']:
        names.append(name)

    parametrization_dict = conf.ospd_data.get('node_checks', {})
    new_parametrizations = []
    new_idlist = []

    for params in parametrizations:
        provider = params[provider_index]
        for host_type in provider.data['deployed_nodes']:
            assert host_type in ROLE_MAPPING
            common_dict = parametrization_dict.get('common', {})
            specific_dict = parametrization_dict.get(host_type, {})
            check_dict = dict(common_dict, **specific_dict)  # yay
            for check_name, check_data in check_dict.iteritems():
                new_parametrizations.append(params + [host_type, check_data])
                new_idlist.append('{}-{}-{}'.format(provider.key, host_type, check_name))
    testgen.parametrize(metafunc, names, new_parametrizations, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def host(provider, host_type, setup_provider_modscope):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    for quad in Quadicon.all(qtype='host'):
        if '{})'.format(ROLE_MAPPING[host_type]) in quad.name:
            host = Host(name=quad.name)
            host.run_smartstate_analysis()
            wait_for(lambda: is_host_analysis_finished(host.name), delay=15, timeout="10m",
                fail_func=lambda: toolbar.select('Reload'))
            return host
    else:
        pytest.fail('Could not find any {} node for provider {}'.format(host_type, provider.key))


def test_verify_node_detail(provider, host, check):
    """Data-driven test for OSP Director node values checking.

    Prerequisities:
        * An OSP Director provider set up with the SSH key pair.

    Steps:
        * Based on the parametrization verify that there is at least one node of such kind
        * Based on the parametrization check the value in the Node summary against the expected
            values.
    """
    host.load_details(refresh=True)
    op = check['op']
    assert op in OP_MAP
    source_type = check.get('type', 'default')
    if source_type == 'default':
        value = InfoBlock.text(check['title'], check['key'])
        op_value = check['value']
        assert OP_MAP[op](value, op_value), '{} {} {} failed'.format(value, op, op_value)
    else:
        pytest.fail('Cannot check {} yet'.format(source_type))
