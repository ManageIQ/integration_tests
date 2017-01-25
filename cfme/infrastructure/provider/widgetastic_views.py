# -*- coding: utf-8 -*-
from widgetastic.widget import View
from widgetastic_patternfly import Button, Dropdown


class ToolBarViewSelector(View):
    """ represents toolbar's view selector control

        .. code-block:: python
        @View.nested
        class view_selector(ToolBarViewSelector):  # NOQA
        
        some_view.view_selector.select('Tile View')
        some_view.view_selector.selected
    """
    ROOT = './/div[contains(@class, "toolbar-pf-view-selector")]'
    BUTTONS = './/button'

    @property
    def _view_buttons(self):
        br = self.browser
        return [Button(self, title=br.get_attribute('title', btn)) for btn
                in br.elements(self.BUTTONS)]

    def select(self, title):
        for button in self._view_buttons:
            if button.title == title:
                return button.click()
        else:
            raise ValueError('Incorrect button title passed')

    @property
    def selected(self):
        """
        Returns: title of currently selected view
        """
        return [btn.title for btn in self._view_buttons if btn.active][-1]


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


class ProviderEntities(View):
    """
    should represent the view with different items like providers
    """

    @View.nested
    class search(object):  # NOQA
        pass


class ProviderSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    pass
