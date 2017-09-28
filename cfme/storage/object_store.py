# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text
from widgetastic_patternfly import Dropdown, FlashMessages
from widgetastic_manageiq import (DetailsToolBarViewSelector, BaseEntitiesView)

from cfme.base.login import BaseLoggedInPage
from cfme.common import SummaryMixin, Taggable
from cfme.web_ui import mixins
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.appliance import Navigatable


class ObjectStoreContainersToolBar(View):
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    view_selector = View.nested(DetailsToolBarViewSelector)


class ObjectStoreContainersSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    pass


class ObjectStoreContainersView(BaseLoggedInPage):
    """
     represents Main view displaying all Cloud Object Store Containers
    """
    toolbar = View.nested(ObjectStoreContainersToolBar)
    sidebar = View.nested(ObjectStoreContainersSideBar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.entities.title.text == 'Cloud Object Store Containers')


class ObjectStoreContainersDetailsView(BaseLoggedInPage):
    """
     main Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    # todo: the rest of widgets should be defined by FA owner
    toolbar = View.nested(View)

    @property
    def is_displayed(self):
        title = '{name} (Summary)'.format(name=self.context['object'].name)
        return self.logged_in_as_current_user and self.title.text == title


class ObjectStore(Taggable, SummaryMixin, Navigatable):
    """ Automate Model page of Cloud Object Stores

    Args:
        name: Name of Object Store
    """

    def __init__(self, name=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name

    def add_tag(self, tag, **kwargs):
        """Tags the system by given tag"""
        navigate_to(self, 'Details')
        mixins.add_tag(tag, **kwargs)

    def untag(self, tag):
        """Removes the selected tag off the system"""
        navigate_to(self, 'Details')
        mixins.remove_tag(tag)


@navigator.register(ObjectStore, 'All')
class All(CFMENavigateStep):
    VIEW = ObjectStoreContainersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        if self.obj.appliance.version < "5.8":
            self.prerequisite_view.navigation.select('Storage', 'Object Stores')
        else:
            self.prerequisite_view.navigation.select(
                'Storage', 'Object Storage', 'Object Store Containers')

    def resetter(self):
        self.view.toolbar.view_selector.select("Grid View")


@navigator.register(ObjectStore, 'Details')
class Details(CFMENavigateStep):
    VIEW = ObjectStoreContainersDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(self.obj.name).click()
