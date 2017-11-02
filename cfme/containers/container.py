# -*- coding: utf-8 -*-
import random
import itertools

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic_manageiq import Accordion, ManageIQTree, View, Table
from widgetastic_patternfly import VerticalNavigation
from widgetastic.widget import Text
from widgetastic.xpath import quote
from widgetastic.utils import Version, VersionPick

from cfme.containers.provider import (ContainerObjectAllBaseView, ContainerObjectDetailsBaseView,
                                      click_row)
from cfme.common import WidgetasticTaggable, TagPageView
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from cfme.utils import version


class ContainerAllView(ContainerObjectAllBaseView):
    """Containers All view"""
    summary = Text(VersionPick({
        Version.lowest(): '//h3[normalize-space(.) = {}]'.format(quote('All Containers')),
        '5.8': '//h1[normalize-space(.) = {}]'.format(quote('Containers'))
    }))
    containers = Table(locator="//div[@id='list_grid']//table")

    @View.nested
    class Filters(Accordion):  # noqa
        ACCORDION_NAME = "Filters"

        @View.nested
        class Navigation(VerticalNavigation):
            DIV_LINKS_MATCHING = './/div/ul/li/a[contains(text(), {txt})]'

            def __init__(self, parent, logger=None):
                VerticalNavigation.__init__(self, parent, '#Container_def_searches', logger=logger)

        tree = ManageIQTree()

    @property
    def is_displayed(self):
        return self.summary.is_displayed


class ContainerDetailsView(ContainerObjectDetailsBaseView):
    pass


class Container(WidgetasticTaggable, Navigatable):

    PLURAL = 'Containers'
    all_view = ContainerAllView
    details_view = ContainerDetailsView

    def __init__(self, name, pod, appliance=None):
        self.name = name
        self.pod = pod
        Navigatable.__init__(self, appliance=appliance)

    @property
    def project_name(self):
        return self.pod.project_name

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        containers_list = provider.mgmt.list_container()
        random.shuffle(containers_list)
        return [cls(obj.name, obj.cg_name, appliance=appliance)
                for obj in itertools.islice(containers_list, count)]


@navigator.register(Container, 'All')
class ContainerAll(CFMENavigateStep):
    VIEW = ContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Containers')

    def resetter(self):
        if version.current_version() < '5.8':
            self.view.Filters.tree.click_path('All Containers')
        else:
            self.view.Filters.Navigation.select('ALL (Default)')
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        if self.view.paginator.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(Container, 'Details')
class ContainerDetails(CFMENavigateStep):
    VIEW = ContainerDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        click_row(self.prerequisite_view,
                  name=self.obj.name, pod_name=self.obj.pod)


@navigator.register(Container, 'EditTags')
class ContainerEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Container, 'Timelines')
class ContainerTimeLines(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Container, 'Utilization')
class ContainerUtilization(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
