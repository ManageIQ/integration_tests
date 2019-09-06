# -*- coding: utf-8 -*-
from collections import namedtuple

import pytest

from cfme import test_requirements
from cfme.containers.container import ContainerAllView
from cfme.containers.image_registry import ImageRegistryAllView
from cfme.containers.node import NodeAllView
from cfme.containers.overview import ContainersOverviewView
from cfme.containers.pod import PodAllView
from cfme.containers.project import ProjectAllView
from cfme.containers.provider import ContainerProvidersView
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import ReplicatorAllView
from cfme.containers.route import RouteAllView
from cfme.containers.service import ServiceAllView
from cfme.containers.template import TemplateAllView
from cfme.containers.volume import VolumeAllView
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


DataSet = namedtuple('DataSet', ['obj_view', 'page_name'])
data_sets = (
    DataSet(ContainersOverviewView, 'Compute / Containers / Overview'),
    DataSet(ContainerProvidersView, 'Compute / Containers / Providers'),
    DataSet(NodeAllView, 'Compute / Containers / Container Nodes'),
    DataSet(PodAllView, 'Compute / Containers / Pods'),
    DataSet(ServiceAllView, 'Compute / Containers / Container Services'),
    DataSet(ProjectAllView, 'Compute / Containers / Projects'),
    DataSet(ImageRegistryAllView, 'Compute / Containers / Image Registries'),
    DataSet(TemplateAllView, 'Compute / Containers / Container Templates'),
    DataSet(ReplicatorAllView, 'Compute / Containers / Replicators'),
    DataSet(RouteAllView, 'Compute / Containers / Routes'),
    DataSet(VolumeAllView, 'Compute / Containers / Volumes'),
    DataSet(ContainerAllView, 'Compute / Containers / Containers'))


def test_start_page(appliance, soft_assert):

    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    for data_set in data_sets:
        appliance.user.my_settings.visual.login_page = data_set.page_name
        login_page = navigate_to(appliance.server, 'LoginScreen')
        login_page.login_admin()
        view = appliance.browser.create_view(data_set.obj_view)
        soft_assert(
            view.is_displayed,
            'Configured start page is "{page_name}", but the start page now is "{cur_page}".'
            .format(page_name=data_set.page_name, cur_page=view.navigation.currently_selected)
        )
