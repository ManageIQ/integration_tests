# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable, paginator, match_location, InfoBlock,\
    flash, PagedTable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.appliance import Navigatable
from cfme.configure import tasks
from wait_for import TimedOutError

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


match_page = partial(match_location, controller='container_image',
                     title='Images')


class Image(Taggable, SummaryMixin, Navigatable):

    def __init__(self, name, tag, provider, appliance=None):
        self.name = name
        self.tag = tag
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    # TODO: remove load_details and dynamic usage from cfme.common.Summary when nav is more complete
    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: Table name and Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the summary's value.
        """
        navigate_to(self, 'Details')
        return InfoBlock.text(*ident)

    def perform_smartstate_analysis(self, wait_for_finish=False):
        """Performing SmartState Analysis on this Image
        """
        navigate_to(self, 'Details')
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_contain('Analysis successfully initiated')
        if wait_for_finish:
            ssa_timeout = '10M'
            try:
                tasks.wait_analysis_finished('Container image analysis',
                                             'vm', delay=5, timeout=ssa_timeout)
            except TimedOutError:
                raise TimedOutError('Timeout exceeded, Waited too much time for SSA to finish ({}).'
                                    .format(ssa_timeout))


@navigator.register(Image, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Images')

    def resetter(self):
        tb.select('Grid View')
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Image, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Name': self.obj.name,
                                                           'Tag': self.obj.tag}))
