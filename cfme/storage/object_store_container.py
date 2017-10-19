# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import (
    Accordion,
    BaseEntitiesView,
    BreadCrumb,
    ItemsToolBarViewSelector,
    ManageIQTree,
    SummaryTable,
)
from widgetastic_patternfly import Button, Dropdown, FlashMessages
from widgetastic.widget import View, Text

from cfme.base.ui import BaseLoggedInPage
from cfme.common import TagPageView, WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.modeling.base import BaseCollection, BaseEntity


class ObjectStoreContainerToolbar(View):
    """The toolbar on the Object Store Containers page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ObjectStoreContainerDetailsToolbar(View):
    """The toolbar on the Object Store Containers detail page"""
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class ObjectStoreContainerDetailsEntities(View):
    """The entities on the Object Store Containers detail page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class ObjectStoreContainerDetailSidebar(View):
    """The accordion on the Object Store Containers details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class ObjectStoreContainerView(BaseLoggedInPage):
    """A base view for all the Object Store Containers pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')
    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]')

    @property
    def in_container(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Storage', 'Object Storage',
                                                   'Object Store Containers'])


class ObjectStoreContainerAllView(ObjectStoreContainerView):
    """The all Object Store Containers page"""
    toolbar = View.nested(ObjectStoreContainerToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_container and
            self.title.text == 'Cloud Object Store Containers')


class ObjectStoreContainerDetailsView(ObjectStoreContainerView):
    """The detail Object Store containers page"""
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].key)

        return (
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ObjectStoreContainerDetailsToolbar)
    sidebar = View.nested(ObjectStoreContainerDetailSidebar)
    entities = View.nested(ObjectStoreContainerDetailsEntities)


@attr.s
class ObjectStoreContainer(BaseEntity, WidgetasticTaggable):
    """ Model of an Storage Object Store Containers in cfme

    Args:
        key: key of the container.
        provider: provider
    """
    key = attr.ib()
    provider = attr.ib()
    # TODO add create method after BZ 1490320 fix


@attr.s
class ObjectStoreContainerCollection(BaseCollection):
    """Collection object for :py:class:'cfme.storage.object_store_container.ObjectStoreContainer'
    """
    ENTITY = ObjectStoreContainer

    def all(self):
        """returning all containers objects"""
        view = navigate_to(self, 'All')
        containers = [self.instantiate(key=item, provider=self.filters.get('provider'))
                      for item in view.entities.all_entity_names]
        return containers


@navigator.register(ObjectStoreContainerCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ObjectStoreContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        if self.obj.appliance.version < "5.8":
            self.prerequisite_view.navigation.select('Storage', 'Object Stores')
        else:
            self.prerequisite_view.navigation.select(
                'Storage', 'Object Storage', 'Object Store Containers')

    def resetter(self):
        self.view.toolbar.view_selector.select("Grid View")


@navigator.register(ObjectStoreContainer, 'Details')
class Details(CFMENavigateStep):
    VIEW = ObjectStoreContainerDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(self.obj.key,
                                                       surf_pages=True).click()
        except ItemNotFound:
            raise ItemNotFound('Could not locate container {}'.format(self.obj.key))


@navigator.register(ObjectStoreContainer, 'EditTagsFromDetails')
class ObjectDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to WidgetasticTaggable"""
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
