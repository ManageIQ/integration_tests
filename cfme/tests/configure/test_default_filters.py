# -*- coding: utf-8 -*-

from xml.sax.saxutils import quoteattr

import pytest

from cfme import test_requirements
from cfme.cloud.instance import Instance
from cfme.cloud.instance.image import Image
from cfme.configure import settings as st
from cfme.infrastructure import virtual_machines as vms
from cfme.services import workloads
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures("infra_provider")]


def test_cloudimage_defaultfilters(appliance):
    filters = [['Cloud', 'Instances', 'Images', 'Platform / Amazon']]
    df = st.DefaultFilter(name='Platform / Amazon')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(Image, 'All')
    loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
    assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"


def test_cloudinstance_defaultfilters(appliance):
    filters = [['Cloud', 'Instances', 'Instances', 'Platform / Openstack']]
    df = st.DefaultFilter(name='Platform / Openstack')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(Instance, 'All')
    loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
    assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"


def test_infrastructurehost_defaultfilters(appliance):
    filters = [['Infrastructure', 'Hosts', 'Platform / HyperV']]
    df = st.DefaultFilter(name='Platform / HyperV')
    df.update({'filters': [(k, True) for k in filters]})
    host_collecton = appliance.collections.hosts
    navigate_to(host_collecton, 'All')
    loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
    assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"


def test_infrastructurevms_defaultfilters(appliance):
    filters = [['Infrastructure', 'Virtual Machines', 'VMs', 'Platform / VMware']]
    df = st.DefaultFilter(name='Platform / VMware')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(vms.Vm, 'VMsOnly')
    loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
    assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"


def test_infrastructuretemplates_defaultfilters(appliance):
    filters = [['Infrastructure', 'Virtual Machines', 'Templates', 'Platform / Redhat']]
    df = st.DefaultFilter(name='Platform / Redhat')
    df.update({'filters': [(k, True) for k in filters]})
    navigate_to(vms.Template, 'TemplatesOnly')
    loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
    assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"


@pytest.mark.meta(blockers=[BZ(1290300, forced_streams=["upstream"])])
def test_servicetemplateandimages_defaultfilters(appliance):
    filters = [['Services', 'Workloads', 'Templates & Images', 'Platform / Microsoft']]
    df = st.DefaultFilter(name='Platform / Microsoft')
    df.update({'filters': [(k, True) for k in filters]})
    try:
        view = navigate_to(workloads.TemplatesImages, 'All')
        view.templates.select_global_filter(df.name)
        loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
        assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"
    finally:
        df.update({'filters': [(k, False) for k in filters]})


def test_servicevmsandinstances_defaultfilters(appliance):
    filters = [['Services', 'Workloads', 'VMs & Instances', 'Platform / Openstack']]
    df = st.DefaultFilter(name='Platform / Openstack')
    df.update({'filters': [(k, True) for k in filters]})
    try:
        view = navigate_to(workloads.VmsInstances, 'All')
        view.vms.select_global_filter(df.name)
        loc = "//*[normalize-space(text())={}]".format(quoteattr(df.name))
        assert appliance.browser.widgetastic.is_displayed(loc), "Default Filter settings Failed!"
    finally:
        df.update({'filters': [(k, False) for k in filters]})
