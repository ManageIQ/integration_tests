# -*- coding: utf-8 -*-
from collections import namedtuple

import pytest

from cfme.configure import settings
from cfme.containers.overview import ContainersOverviewView
from cfme.containers.node import NodeAllView
from cfme.containers.pod import PodAllView
from cfme.containers.service import ServiceAllView
from cfme.containers.provider import ContainersProvider, ContainerProvidersView
from cfme.containers.project import ProjectAllView
from cfme.containers.image_registry import ImageRegistryAllView
from cfme.containers.template import TemplateAllView
from cfme.containers.replicator import ReplicatorAllView
from cfme.containers.route import RouteAllView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.8"),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([ContainersProvider], scope='function')
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
    # https://bugzilla.redhat.com/show_bug.cgi?id=1510376
    # from cfme.containers.volume import VolumeAllView
    #  DataSet(VolumeAllView, 'Compute / Containers / Volumes'),
    # https://bugzilla.redhat.com/show_bug.cgi?id=1466350
    # from cfme.containers.container import ContainerAllView
    # DataSet(ContainerAllView, 'Compute / Containers / Containers')
)


@pytest.mark.polarion('CMP-10601')
def test_start_page(appliance, soft_assert):

    for data_set in data_sets:
        settings.visual.login_page = data_set.page_name
        login_page = navigate_to(appliance.server, 'LoginScreen')
        login_page.login_admin()
        view = appliance.browser.create_view(data_set.obj_view)
        soft_assert(
            view.is_displayed,
            'Configured start page is "{page_name}", but the start page now is "{cur_page}".'
            .format(page_name=data_set.page_name, cur_page=view.navigation.currently_selected)
        )
