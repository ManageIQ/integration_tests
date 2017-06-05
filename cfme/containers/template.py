# -*- coding: utf-8 -*-
import random
from functools import partial

from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import SummaryMixin, Taggable
from cfme.containers.provider import Labelable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, paginator, match_location,\
    PagedTable, CheckboxTable
from .provider import details_page
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep,\
    navigate_to

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container_templates', title='Container Templates')


class Template(Taggable, Labelable, SummaryMixin, Navigatable):

    def __init__(self, name, project_name, provider, appliance=None):
        self.name = name
        self.project_name = project_name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

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
        template_list = provider.mgmt.list_template()
        instances = []
        random.shuffle(template_list)
        while template_list and len(instances) < count:
            chosen = template_list.pop()
            instances.append(
                cls(chosen.name, chosen.project_name, provider, appliance=appliance)
            )
        return instances


@navigator.register(Template, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Templates')

    def resetter(self):
        # Reset view and selection
        tb.select("List View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Template, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Name': self.obj.name,
                                                           'Project Name': self.obj.project_name}))
