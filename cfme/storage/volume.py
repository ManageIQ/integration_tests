# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import (
    Accordion,
    BaseEntitiesView,
    BaseListEntity,
    BaseQuadIconEntity,
    BaseTileIconEntity,
    BootstrapSelect,
    BreadCrumb,
    ItemsToolBarViewSelector,
    JSBaseEntity,
    ManageIQTree,
    NonJSBaseEntity,
    SummaryTable,
    TextInput,
    Version,
    VersionPick
)
from widgetastic_patternfly import Button, Dropdown, FlashMessages
from widgetastic.widget import View, Text, ParametrizedView

from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import VolumeNotFound, ItemNotFound
from cfme.web_ui import match_location
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.appliance import NavigatableMixin
from utils.log import logger
from utils.wait import wait_for, TimedOutError


class VolumeToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # title match
    view_selector = View.nested(ItemsToolBarViewSelector)


class VolumeDetailsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Download summary in PDF format')


class VolumeQuadIconEntity(BaseQuadIconEntity):
    pass


class VolumeTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(VolumeQuadIconEntity)


class VolumeListEntity(BaseListEntity):
    pass


class NonJSVolumeEntity(NonJSBaseEntity):
    quad_entity = VolumeQuadIconEntity
    list_entity = VolumeListEntity
    tile_entity = VolumeTileIconEntity


def VolumeEntity():  # noqa
    """Temporary wrapper for Volume Entity during transition to JS based Entity """
    return VersionPick({
        Version.lowest(): NonJSVolumeEntity,
        '5.9': JSBaseEntity,
    })


class VolumeEntities(BaseEntitiesView):
    """The entities on the main list of Volume Page"""

    @property
    def entity_class(self):
        return VolumeEntity().pick(self.browser.product_version)


class VolumeDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class VolumeDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class VolumeView(BaseLoggedInPage):
    """Base class for header and nav check"""
    @property
    def in_volume(self):
        nav = Volume.nav.pick(self.context['object'].appliance.version)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav and
            match_location(controller='cloud_volume', title='Cloud Volumes'))


class VolumeAllView(VolumeView):
    toolbar = View.nested(VolumeToolbar)
    including_entities = View.include(VolumeEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_volume and
            self.entities.title.text == 'Cloud Volumes'
        )


class VolumeDetailsView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        # The field in relationships table changes based on volume status so look for either
        try:
            provider = self.entities.relationships.get_text_of('Cloud Provider')
        except NameError:
            provider = self.entities.relationships.get_text_of('Parent Cloud Provider')
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title and
            provider == self.context['object'].provider.name)

    toolbar = View.nested(VolumeDetailsToolbar)
    sidebar = View.nested(VolumeDetailsAccordion)
    entities = View.nested(VolumeDetailsEntities)


class VolumeAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeAddForm(View):
    volume_name = TextInput(name='name')
    size = TextInput(name='size')
    tenant = BootstrapSelect(id='cloud_tenant_id')
    add = Button('Add')
    cancel = Button('Cancel')


class VolumeAddView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = "Add New Cloud Volume"
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    entities = View.nested(VolumeAddEntities)
    form = View.nested(VolumeAddForm)


class VolumeCollection(NavigatableMixin):
    """Collection object for the :py:class:'cfme.storage.volume.Volume'. """

    def __init__(self, appliance):
        self.appliance = appliance

    def instantiate(self, name, provider):
        return Volume(name, provider, collection=self)

    def delete(self, *volumes):
        """Delete one or more Volumes from list of Volumes

        Args:
            One or Multiple 'cfme.storage.volume.Volume' objects
        """

        view = navigate_to(self, 'All')

        if view.entities.get_all():
            for volume in volumes:
                try:
                    view.entities.get_entity(volume.name).check()
                except ItemNotFound:
                    raise VolumeNotFound("Volume {} not found".format(volume.name))

            view.toolbar.configuration.item_select('Delete selected Cloud Volumes',
                                                   handle_alert=True)

            for volume in volumes:
                volume.wait_for_disappear()
        else:
            raise VolumeNotFound('No Cloud Volume for Deletion')


class Volume(NavigatableMixin):
    # Navigation menu option
    nav = VersionPick({
        Version.lowest(): ['Storage', 'Volumes'],
        '5.8': ['Storage', 'Block Storage', 'Volumes']})

    def __init__(self, name, provider, collection):
        self.name = name
        # TODO add storage provider parameter, needed for accurate details nav
        # the storage providers have different names then cloud providers
        # https://bugzilla.redhat.com/show_bug.cgi?id=1455270
        self.provider = provider
        self.collection = collection
        self.appliance = self.collection.appliance

    def wait_for_disappear(self, timeout=300):
        def refresh():
            self.provider.refresh_provider_relationships()
            self.browser.refresh()

        try:
            wait_for(lambda: not self.exists,
                     timeout=timeout,
                     message='Wait for cloud Volume to disappear',
                     delay=20,
                     fail_func=refresh)
        except TimedOutError:
            logger.error('Timed out waiting for Volume to disappear, continuing')

    def delete(self, wait=True):
        """Delete the Volume"""

        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Cloud Volume', handle_alert=True)

        view.entities.flash.assert_success_message('Delete initiated for 1 Cloud Volume.')

        if wait:
            self.wait_for_disappear(500)

    @property
    def exists(self):
        view = navigate_to(self.collection, 'All')
        try:
            view.entities.get_entity(by_name=self.name, surf_pages=True)
            return True
        except ItemNotFound:
            return False


@navigator.register(VolumeCollection, 'All')
class VolumeAll(CFMENavigateStep):
    VIEW = VolumeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = Volume.nav.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(Volume, 'Details')
class VolumeDetails(CFMENavigateStep):
    VIEW = VolumeDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):

        try:
            self.prerequisite_view.entities.get_entity(by_name=self.obj.name,
                                                       surf_pages=True).click()

        except ItemNotFound:
            raise VolumeNotFound('Volume {} not found'.format(self.obj.name))


@navigator.register(VolumeCollection, 'Add')
class VolumeAdd(CFMENavigateStep):
    VIEW = VolumeAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Volume')
