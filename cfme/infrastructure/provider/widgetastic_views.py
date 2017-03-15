# -*- coding: utf-8 -*-
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown
from widgetastic_manageiq import ItemsToolBarViewSelector


class ProviderToolBar(View):
    """
    represents provider toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    authentication = Dropdown(text='Authentication')
    download = Dropdown(text='Download')

    @View.nested
    class view_selector(ItemsToolBarViewSelector):  # NOQA
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
