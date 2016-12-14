# -*- coding: utf-8 -*-

import pytest
from cfme import test_requirements
from cfme.configure import settings as st
from cfme.fixtures import pytest_selenium as sel
from utils.blockers import BZ
from utils.providers import setup_a_provider
from cfme.cloud.instance.image import Image
from cfme.cloud.instance import Instance
from cfme.infrastructure import virtual_machines as vms
from cfme.services import workloads
from utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.host import Host

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)


def test_cloudimage_defaultfilters(setup_first_provider):
    filters = [['Cloud', 'Instances', 'Images', 'Platform / Amazon']]
    df = st.DefaultFilter(name='Platform / Amazon')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(Image, 'All')
    assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"


def test_cloudinstance_defaultfilters(setup_first_provider):
    filters = [['Cloud', 'Instances', 'Instances', 'Platform / Openstack']]
    df = st.DefaultFilter(name='Platform / Openstack')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(Instance, 'All')
    assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"


def test_infrastructurehost_defaultfilters(setup_first_provider):
    filters = [['Infrastructure', 'Hosts', 'Platform / HyperV']]
    df = st.DefaultFilter(name='Platform / HyperV')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(Host, 'All')
    assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"


def test_infrastructurevms_defaultfilters(setup_first_provider):
    filters = [['Infrastructure', 'Virtual Machines', 'VMs', 'Platform / VMware']]
    df = st.DefaultFilter(name='Platform / VMware')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(vms.Vm, 'VMsOnly', filter_folder='Global Filters')
    assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"


def test_infrastructuretemplates_defaultfilters(setup_first_provider):
    filters = [['Infrastructure', 'Virtual Machines', 'Templates', 'Platform / Redhat']]
    df = st.DefaultFilter(name='Platform / Redhat')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(vms.Template, 'TemplatesOnly', filter_folder='Global Filters')
    assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"


@pytest.mark.meta(blockers=[BZ(1290300, forced_streams=["upstream"])])
def test_servicetemplateandimages_defaultfilters(setup_first_provider):
    filters = [['Services', 'Workloads', 'Templates & Images', 'Platform / Microsoft']]
    df = st.DefaultFilter(name='Platform / Microsoft')
    df.update({'filters': [(k, True) for k in filters]})
    try:
        navigate_to(workloads.VmsInstances, 'All', filter_folder='Global Filters',
                    filter_name=df.name)
        assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"
    finally:
        df.update({'filters': [(k, False) for k in filters]})


def test_servicevmsandinstances_defaultfilters(setup_first_provider):
    filters = [['Services', 'Workloads', 'VMs & Instances', 'Platform / Openstack']]
    df = st.DefaultFilter(name='Platform / Openstack')
    df.update({'filters': [(k, True) for k in filters]})
    try:
        navigate_to(workloads.TemplatesImages, 'All', filter_folder='Global Filters',
                    filter_name=df.name)
        assert sel.is_displayed_text(df.name), "Default Filter settings Failed!"
    finally:
        df.update({'filters': [(k, False) for k in filters]})
