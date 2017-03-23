# -*- coding: utf-8 -*-
from widgetastic.widget import View, Text
from widgetastic_patternfly import Dropdown, Button
from widgetastic_manageiq import ItemsToolBarViewSelector, DetailsToolBarViewSelector, Search


class ProviderToolBar(View):
    """
    represents provider toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')
    download = Dropdown(text='Download')
    view_selector = ItemsToolBarViewSelector()


class ProviderEntities(View):
    """
    should represent the view with different items like providers
    """
    title = Text('//div[@id="main-content"]//h1')

    @View.nested
    class search(Search):  # NOQA
        pass


class ProviderSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
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
    class view_selector(DetailsToolBarViewSelector):  # NOQA
        pass
