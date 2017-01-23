# -*- coding: utf-8 -*-
from widgetastic.widget import View
from widgetastic_patternfly import Button, Dropdown


class BaseToolBarViewSelector(View):
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
        elif item == self.grid_view.title:
            self.grid_view.click()
        elif item == self.tile_view.title:
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
    class view_selector(BaseToolBarViewSelector):  # NOQA
        pass


class Items(View):
    """
    should represent the view with different items like providers
    """

    @View.nested
    class search(object):  # NOQA
        pass


class BaseSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    pass