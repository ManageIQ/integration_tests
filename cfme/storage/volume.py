# -*- coding: utf-8 -*-
import attr

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
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, TimedOutError


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
            self.navigation.currently_selected == nav)


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
    storage_manager = BootstrapSelect(name='storage_manager_id')
    volume_name = TextInput(name='name')
    size = TextInput(name='size')
    tenant = BootstrapSelect(name='cloud_tenant_id')
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


class VolumeEditView(VolumeView):
    @property
    def is_displayed(self):
        return False

    volume_name = TextInput(name='name')
    save = Button('Save')


@attr.s
class Volume(BaseEntity):
    # Navigation menu option
    nav = VersionPick({
        Version.lowest(): ['Storage', 'Volumes'],
        '5.8': ['Storage', 'Block Storage', 'Volumes']})

    name = attr.ib()
    provider = attr.ib()

    def wait_for_disappear(self, timeout=300):
        """Wait for disappear the volume"""
        try:
            wait_for(lambda: not self.exists,
                     timeout=timeout,
                     message='Wait for cloud Volume to disappear',
                     delay=20,
                     fail_func=self.refresh)
        except TimedOutError:
            logger.error('Timed out waiting for Volume to disappear, continuing')

    def edit(self, name):
        """Edit cloud volume"""
        view = navigate_to(self, 'Edit')
        view.volume_name.fill(name)
        view.save.click()

        # Wrong flash for 5.7[BZ-1506992]. As BZ clear 5.7 will consistence with 5.8 and 5.9.
        if self.appliance.version < "5.8":
            view.flash.assert_success_message('Updating Cloud Volume "{}"'.format(self.name))
        else:
            view.flash.assert_success_message('Cloud Volume "{}" updated'.format(name))

        self.name = name
        wait_for(lambda: self.exists, delay=20, timeout=500, fail_func=self.refresh)

    def delete(self, wait=True):
        """Delete the Volume"""

        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Cloud Volume', handle_alert=True)

        view.entities.flash.assert_success_message('Delete initiated for 1 Cloud Volume.')

        if wait:
            self.wait_for_disappear(500)

    def refresh(self):
        """Refresh provider relationships and browser"""
        self.provider.refresh_provider_relationships()
        self.browser.refresh()

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except VolumeNotFound:
            return False

    @property
    def size(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Size')

    @property
    def tenant(self):
        view = navigate_to(self, 'Details')
        return view.entities.relationships.get_text_of('Cloud Tenants')


@attr.s
class VolumeCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.storage.volume.Volume'. """
    ENTITY = Volume

    def create(self, name, storage_manager, tenant, size, provider):
        """Create new storage volume

        Args:
            name: volume name
            storage_manager: storage manager name
            tenant: tenant name
            size: volume size in GB
            provider: provider

        Returns:
            object for the :py:class: cfme.storage.volume.Volume
        """

        view = navigate_to(self, 'Add')
        view.form.fill({'storage_manager': storage_manager,
                        'tenant': tenant,
                        'volume_name': name,
                        'size': size})
        view.form.add.click()
        base_message = VersionPick({
            Version.lowest(): 'Creating Cloud Volume "{}"',
            '5.8': 'Cloud Volume "{}" created'}).pick(self.appliance.version)
        view.flash.assert_success_message(base_message.format(name))

        volume = self.instantiate(name, provider)
        wait_for(lambda: volume.exists, delay=20, timeout=500, fail_func=volume.refresh)

        return volume

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
    prerequisite = NavigateToAttribute('parent', 'All')

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


@navigator.register(Volume, 'Edit')
class VolumeEdit(CFMENavigateStep):
    VIEW = VolumeEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Cloud Volume')
