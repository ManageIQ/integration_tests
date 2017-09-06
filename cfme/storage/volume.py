# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text, NoSuchElementException
from widgetastic_patternfly import Button, Dropdown, FlashMessages
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, Search, Table, PaginationPane, BreadCrumb, SummaryTable, Accordion,
    ManageIQTree, TextInput, BootstrapSelect, VersionPick, Version, BootstrapSwitch)

from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import VolumeNotFound
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator
from utils.log import logger


class VolumeToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # title match
    view_selector = View.nested(ItemsToolBarViewSelector)


class VolumeDetailsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Download summary in PDF format')


class VolumeEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    search = View.nested(Search)
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')


class VolumeDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


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
            self.navigation.currently_selected == nav
        )


class VolumeAllView(VolumeView):
    @property
    def is_displayed(self):
        return (
            self.in_volume and
            self.entities.title.text == 'Cloud Volumes')

    toolbar = View.nested(VolumeToolbar)
    entities = View.nested(VolumeEntities)
    paginator = PaginationPane()


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
    # Commented lines won't work until this issue is fixed:
    # https://github.com/ManageIQ/integration_tests/issues/5134
    # block_manager = BootstrapSelect(name='storage_manager_id')
    volume_name = TextInput(name='name')
    size = TextInput(name='size')
    # tenant is for openstack block storage only
    tenant = BootstrapSelect(id='cloud_tenant_id')
    add = Button('Add')
    cancel = Button('Cancel')
    # fields under this comment are for aws ebs only
    # az = BootstrapSelect(name='aws_availability_zone_id')
    # type = BootstrapSelect(name='aws_volume_type')
    iops = TextInput(name='aws_iops')
    encryption = BootstrapSwitch(name="aws_encryption")


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


class VolumeCreateSnapshotEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeCreateSnapshotForm(View):
    snapshot_name = TextInput(name='snapshot_name')
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class VolumeCreateSnapshotView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = "Create Snapshot for Cloud Volume"
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    entities = View.nested(VolumeCreateSnapshotEntities)
    form = View.nested(VolumeCreateSnapshotForm)


class VolumeAttachEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeAttachForm(View):
    instance = BootstrapSelect('vm_id')
    device_path = TextInput(name='device_path')
    attach = Button('Attach')
    reset = Button('Reset')
    cancel = Button('Cancel')


class VolumeAttachView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = "Attach Cloud Volume"
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    entities = View.nested(VolumeAttachEntities)
    form = View.nested(VolumeAttachForm)


class VolumeDetachEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeDetachForm(View):
    instance = BootstrapSelect('vm_id')
    detach = Button('Detach')
    cancel = Button('Cancel')


class VolumeDetachView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = "Detach Cloud Volume"
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    entities = View.nested(VolumeDetachEntities)
    form = View.nested(VolumeDetachForm)


class VolumeEditEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class VolumeEditForm(View):
    # Commented lines won't work until this issue is fixed:
    # https://github.com/ManageIQ/integration_tests/issues/5134
    # block_manager = BootstrapSelect(name='storage_manager_id')
    # az = BootstrapSelect(name='aws_availability_zone_id')
    volume_name = TextInput(name='name')
    # type = BootstrapSelect(name='aws_volume_type')
    size = TextInput(name='size')
    iops = TextInput(name='aws_iops')
    encryption = BootstrapSwitch(name="aws_encryption")
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class VolumeEditView(VolumeView):
    @property
    def is_displayed(self):
        expected_title = "Edit Cloud Volume"
        return (
            self.in_volume and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    entities = View.nested(VolumeEditEntities)
    form = View.nested(VolumeEditForm)


class Volume(Navigatable):
    # Navigation menu option
    nav = VersionPick({
        Version.lowest(): ['Storage', 'Volumes'],
        '5.8': ['Storage', 'Block Storage', 'Volumes']})

    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        # TODO add storage provider parameter, needed for accurate details nav
        # the storage providers have different names then cloud providers
        # https://bugzilla.redhat.com/show_bug.cgi?id=1455270
        self.provider = provider


@navigator.register(Volume, 'All')
class VolumeAll(CFMENavigateStep):
    VIEW = VolumeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav = Volume.nav.pick(self.obj.appliance.version)
        self.prerequisite_view.navigation.select(*nav)


@navigator.register(Volume, 'Details')
class VolumeDetails(CFMENavigateStep):
    VIEW = VolumeDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name, cloud_provider=self.obj.provider.name)
        except NoSuchElementException:
            logger.warn('Cannot identify volume by name and provider, looking by name only')
            try:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table, name=self.obj.name)
            except NoSuchElementException:
                raise VolumeNotFound
        row.click()


@navigator.register(Volume, 'Add')
class VolumeAdd(CFMENavigateStep):
    VIEW = VolumeAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Cloud Volume')


@navigator.register(Volume, 'CreateSnapshot')
class VolumeCreateSnapshot(CFMENavigateStep):
    VIEW = VolumeCreateSnapshotView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            "Create a Snapshot of this Cloud Volume"
        )


@navigator.register(Volume, 'Attach')
class VolumeAttach(CFMENavigateStep):
    VIEW = VolumeAttachView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            "Attach this Cloud Volume to an Instance"
        )


@navigator.register(Volume, 'Detach')
class VolumeDetach(CFMENavigateStep):
    VIEW = VolumeDetachView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            "Detach this Cloud Volume from an Instance"
        )


@navigator.register(Volume, 'Edit')
class VolumeEditor(CFMENavigateStep):
    VIEW = VolumeEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Cloud Volume")
