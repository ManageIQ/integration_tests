# -*- coding: utf-8 -*-
"""
temporary file for storing widgetastic controls and view which could be shared
"""
from widgetastic.widget import View, Checkbox

from widgetastic_patternfly import Button, BootstrapSelect, Dropdown

from widgetastic_manageiq import Search, Stepper, Calendar, BreadCrumb, RadioGroup


class ToolBarViewSelector(View):
    """
    represents toolbar's view selector control.
    """
    list_view = Button(title='List View')
    grid_view = Button(title='Grid View')
    tile_view = Button(title='Tile View')

    def __locator__(self):
        return './/div[contains(@class, "toolbar-pf-view-selector")]'

    def select(self, item):
        if item == self.list_view.title:
            self.list_view.click()
        elif item == 'Grid View':
            self.grid_view.click()
        elif item == 'Tile View':
            self.grid_view.click()
        else:
            raise ValueError('Incorrect value passed')

    @property
    def selected(self):
        """
        goes thru buttons and returns the title of active button
        Returns: currently selected view

        """
        return [btn.title for btn in (self.list_view, self.grid_view, self.tile_view)
                if btn.active][-1]


class ProviderToolBar(View):
    """
    represents provider toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')
    download = Dropdown(text='Download')

    @View.nested
    class view_selector(ToolBarViewSelector):  # NOQA
        pass


class DetailsProviderToolBar(View):
    """
    represents provider toolbar and its controls
    """
    monitoring = Dropdown(text='Monitoring')
    configuration = Dropdown(text='Configuration')
    reload = Button(title='Reload Current Display')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')

    @View.nested
    class view_selector(ToolBarViewSelector):  # NOQA
        # todo: there should be another ViewSelector. to add it later
        pass


class Items(View):
    """
    should represent the view with different items like providers
    """

    @View.nested
    class search(Search):  # NOQA
        pass


class BaseSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    pass


class TimelinesFilter(View):
    def __init__(self, parent, filter_type, logger=None):
        super(TimelinesFilter, self).__init__(parent=parent, logger=logger)
        if filter_type in ('Management Events', 'Policy Events'):
            self._filter_type = filter_type
        else:
            raise ValueError('incorrect filter type is passed')

    # common
    event_type = BootstrapSelect(id='tl_show')
    event_category = BootstrapSelect(id='tl_category_management')
    time_period = Stepper()
    time_range = BootstrapSelect(id='tl_range')
    time_position = BootstrapSelect(id='tl_timepivot')
    date_picker = Calendar()
    apply = Button("Apply")
    # management controls
    detailed_events = Checkbox(name='showDetailedEvents')
    # policy controls
    event_category = BootstrapSelect(id='tl_category_policy')
    event_status = RadioGroup()


class TimelinesChart(View):
    # todo: to add widgets for all controls
    # currently only events collection is available
    pass


class Timelines(View):
    """
    represents Timelines page
    """

    @View.nested
    class sidebar(BaseSideBar):  # NOQA
        pass

    breadcrumb = BreadCrumb()

    @View.nested
    class filter(TimelinesFilter):  # NOQA
        pass

    @View.nested
    class chart(TimelinesChart):  # NOQA
        pass
