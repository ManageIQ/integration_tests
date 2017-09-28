# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import (
    Accordion,
    BaseEntitiesView,
    BreadCrumb,
    ItemsToolBarViewSelector,
    ManageIQTree,
    SummaryTable,
    Version,
    VersionPick
)
from widgetastic_patternfly import Button, Dropdown, FlashMessages
from widgetastic.widget import View, Text, NoSuchElementException

from cfme.base.ui import BaseLoggedInPage
from cfme.common import TagPageView, WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.appliance import BaseCollection, BaseEntity


class ObjStoreContainerToolbar(View):
    """The toolbar on the Object Store Containers page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ObjStoreContainerDetailsToolbar(View):
    """The toolbar on the Object Store Containers detail page"""
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class ObjStoreContainerDetailsEntities(View):
    """The entities on the Object Store Containers detail page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class ObjStoreContainerDetailsAccordion(View):
    """The accordion on the Object Store Containers details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class ObjStoreContainerView(BaseLoggedInPage):
    """A base view for all the Object Store Containers pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')
    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]')

    @property
    def in_container(self):
        nav = ObjStoreContainer.nav.pick(self.context['object'].appliance.version)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav)


class ObjStoreContainerAllView(ObjStoreContainerView):
    """The all Object Store Containers page"""
    toolbar = View.nested(ObjStoreContainerToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_container and
            self.title.text in ['Cloud Object Store Containers',
                                'Cloud Object Stores'])


class ObjStoreContainerDetailsView(ObjStoreContainerView):
    """The detail Object Store containers page"""
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].key)

        return (
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ObjStoreContainerDetailsToolbar)
    sidebar = View.nested(ObjStoreContainerDetailsAccordion)
    entities = View.nested(ObjStoreContainerDetailsEntities)


class ObjStoreContainerCollection(BaseCollection):
    """Collection object for :py:class:'cfme.storage.object_store_container.ObjStoreContainer'
    """

    def __init__(self, appliance):
        self.appliance = appliance

    def instantiate(self, key, provider):
        return ObjStoreContainer(self, key, provider)

    def all(self, provider):
        """returning all containers objects"""
        view = navigate_to(self, 'All')
        containers = [self.instantiate(key=item.name, provider=provider)
                 for item in view.entities.get_all()]
        return containers


class ObjStoreContainer(BaseEntity, WidgetasticTaggable):
    """ Model of an Storage Object Store Containers in cfme

    Args:
        key: key of the container.
        provider: provider
    """
    def __init__(self, collection, key, provider):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.key = key
        self.provider = provider

    # TODO add create method after BZ 1490320 fix

    nav = VersionPick({
        Version.lowest(): ['Storage', 'Object Stores'],
        '5.8': ['Storage', 'Object Storage', 'Object Store Containers']})


@navigator.register(ObjStoreContainerCollection, 'All')
class ObjStoreContainerAll(CFMENavigateStep):
    VIEW = ObjStoreContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = ObjStoreContainer.nav.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(ObjStoreContainer, 'Details')
class ObjectDetails(CFMENavigateStep):
    VIEW = ObjStoreContainerDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(by_name=self.obj.key,
                                                       surf_pages=True).click()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate container {}'.format(self.obj.key))


@navigator.register(ObjStoreContainer, 'EditTagsFromDetails')
class ObjectDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to WidgetasticTaggable"""
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
