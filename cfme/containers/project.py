# -*- coding: utf-8 -*-
import random
import itertools

from cached_property import cached_property

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, match_location,\
    PagedTable, CheckboxTable
from cfme.containers.provider import details_page, Labelable,\
    ContainerObjectAllBaseView
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator,\
    navigate_to
from navmazing import NavigateToAttribute, NavigateToSibling
from functools import partial
from wrapanapi.containers.project import Project as ApiProject


list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container_projects', title='Projects')


class Project(Taggable, Labelable, SummaryMixin, Navigatable):

    PLURAL = 'Projects'

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiProject(self.provider.mgmt, self.name)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def click_element(self, *ident):
        self.load_details(refresh=True)
        return sel.click(details_page.infoblock.element(*ident))

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        return details_page.infoblock.text(*ident)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        project_list = provider.mgmt.list_project()
        random.shuffle(project_list)
        return [cls(obj.name, provider, appliance=appliance)
                for obj in itertools.islice(project_list, count)]


class ProjectAllView(ContainerObjectAllBaseView):
    TITLE_TEXT = 'Projects'


@navigator.register(Project, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ProjectAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Projects')

    def resetter(self):
        # Reset view and selection
        tb.select("List View")
        from cfme.web_ui import paginator
        paginator.check_all()
        paginator.uncheck_all()


@navigator.register(Project, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Name': self.obj.name}))
