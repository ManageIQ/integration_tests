# -*- coding: utf-8 -*-
"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""
from collections import namedtuple
from copy import copy

import attr
import fauxfactory
import re

from navmazing import NavigateToSibling, NavigationDestinationNotFound, NavigateToAttribute
from widgetastic.utils import partial_match, Parameter, VersionPick, Version
from widgetastic.widget import (
    Text, View, TextInput, Checkbox, NoSuchElementException, ParametrizedView)
from widgetastic_patternfly import (
    Button, BootstrapSelect, BootstrapSwitch, CheckableBootstrapTreeview, Dropdown, Input as
    WInput)

from cfme.base.login import BaseLoggedInPage
from cfme.common.vm import VM, Template, VMCollection, TemplateCollection
from cfme.common.vm_views import (
    ManagementEngineView, CloneVmView, MigrateVmView, ProvisionView, EditView, PublishVmView,
    RetirementView, RetirementViewWithOffset, VMDetailsEntities, VMToolbar, VMEntities,
    SetOwnershipView)
from cfme.exceptions import (
    OptionNotAvailable, DestinationNotFound, ItemNotFound, VmOrInstanceNotFound)
from cfme.services.requests import RequestsView
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (
    Accordion, ConditionalSwitchableView, ManageIQTree, NonJSPaginationPane,
    SummaryTable, Table, TimelinesView, CompareToolBarActionsView)
from widgetastic_manageiq.vm_reconfigure import DisksTable


def has_child(tree, text, parent_item=None):
    """Check if a tree has an item with text"""
    if not parent_item:
        parent_item = tree.root_item
    if tree.child_items_with_text(parent_item, text):
        return True
    else:
        for item in tree.child_items(parent_item):
            if has_child(tree, text, item):
                return True
    return False


def find_path(tree, text, parent_item=None):
    """Find the path to an item with text"""
    if not parent_item:
        parent_item = tree.root_item
    path = [parent_item.text]
    tree.expand_node(tree.get_nodeid(parent_item))
    children = tree.child_items_with_text(parent_item, text)
    if children:
        for child in children:
            if child.text:
                return path + [child.text]
        return []
    else:
        for item in tree.child_items(parent_item):
            child_path = find_path(tree, text, item)
            if child_path:
                return path + child_path
    return []


class InfraGenericDetailsToolbar(View):
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page',
                                       '6.0': 'Reload current display'}))
    history = Dropdown('History')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown("Monitoring")
    download = Button(title='Download summary in PDF format')
    lifecycle = Dropdown('Lifecycle')

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group", )
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=None):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class InfraVmDetailsToolbar(InfraGenericDetailsToolbar):
    """Toolbar for VM details differs from All VMs&TemplatesView
    """
    access = Dropdown("Access")
    power = Dropdown('VM Power Functions')


class VmsTemplatesAccordion(View):
    """
    The accordion on the Virtual Machines page
    """
    @View.nested
    class vmstemplates(Accordion):  # noqa
        ACCORDION_NAME = 'VMs & Templates'
        tree = ManageIQTree()

    @View.nested
    class vms(Accordion):  # noqa
        ACCORDION_NAME = 'VMs'
        tree = ManageIQTree()

    @View.nested
    class templates(Accordion):  # noqa
        ACCORDION_NAME = 'Templates'
        tree = ManageIQTree()


class InfraVmView(BaseLoggedInPage):
    """Base view for header/nav check, inherit for navigatable views"""

    @property
    def in_infra_vms(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Virtual Machines'])


class VmsTemplatesAllView(InfraVmView):
    """
    The collection page for instances
    """
    actions = View.nested(CompareToolBarActionsView)
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)
    pagination = View.nested(NonJSPaginationPane)

    @property
    def is_displayed(self):
        return (
            self.in_infra_vms and
            self.sidebar.vmstemplates.tree.currently_selected == ['All VMs & Templates'] and
            self.entities.title.text == 'All VMs & Templates')

    def reset_page(self):
        self.entities.search.remove_search_filters()


class VmTemplatesAllForProviderView(InfraVmView):
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        expected_provider = None
        # Could be collection or entity
        # If entity it will have provider attribute
        if getattr(self.context['object'], 'provider', False):
            expected_provider = self.context['object'].provider.name
        # if collection will have provider filter
        elif 'provider' in getattr(self.context['object'], 'filters', {}):
            expected_provider = self.context['object'].filters.get('provider').name

        if expected_provider is None:
            self.logger.warning('No provider available on context for is_displayed: %s',
                                self.context['object'])
            return False
        else:
            return (
                self.in_infra_vms and
                str(self.entities.title.text) ==
                'VM or Templates under Provider "{}"'.format(expected_provider)
            )

    def reset_page(self):
        self.entities.search.remove_search_filters()


class VmsOnlyAllView(InfraVmView):
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_infra_vms and
            self.sidebar.vms.tree.currently_selected == ['All VMs'] and
            self.entities.title.text == 'All VMs')

    def reset_page(self):
        self.entities.search.remove_search_filters()


class TemplatesOnlyAllView(InfraVmView):
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_infra_vms and
            self.sidebar.templates.tree.currently_selected == ['All Templates'] and
            self.entities.title.text == 'All Templates')


class ProviderTemplatesOnlyAllView(TemplatesOnlyAllView):

    @property
    def is_displayed(self):
        text = 'Miq' if self.browser.product_version < "5.9" else 'VM'
        msg = '{} (All {} Templates)'.format(self.context['object'].name, text)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Providers'] and
            self.entities.title.text == msg
        )


class HostTemplatesOnlyAllView(TemplatesOnlyAllView):

    @property
    def is_displayed(self):
        if self.browser.product_version < "5.9":
            title = "{} (All Templates)".format(self.context["object"].name)
        else:
            title = "{} (All VM Templates)".format(self.context["object"].name)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Hosts'] and
            self.entities.title.text == title
        )


class InfraVmSummaryView(VMDetailsEntities):
    operating_ranges = SummaryTable(title="Normal Operating Ranges (over 30 days)")
    datastore_allocation = SummaryTable(title="Datastore Allocation Summary")
    datastore_usage = SummaryTable(title="Datastore Actual Usage Summary")


class InfraVmDetailsView(InfraVmView):
    title = Text('#explorer_title_text')
    toolbar = ConditionalSwitchableView(reference='entities.title')

    @toolbar.register(lambda title: "VM and Instance" in title or "Virtual Machine" in title)
    class VmsToolbar(InfraVmDetailsToolbar):
        pass

    @toolbar.register(lambda title: "VM Template and Image" in title or "Template" in title)
    class TemplatesToolbar(InfraGenericDetailsToolbar):
        pass

    sidebar = View.nested(VmsTemplatesAccordion)
    entities = View.nested(VMDetailsEntities)

    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        expected_provider = self.context['object'].provider.name
        try:
            relationships = self.entities.summary('Relationships')
            relationship_provider_name = relationships.get_text_of('Infrastructure Provider')
        except NameError:
            currently_selected = self.sidebar.vmstemplates.tree.currently_selected[-1]
            if currently_selected in ['<Archived>', '<Orphaned>']:
                return (
                    self.in_infra_vms and
                    self.entities.title.text == 'VM and Instance "{}"'.format(expected_name))
            self.logger.warning('No "Infrastructure Provider" Relationship, VM details view not'
                                ' displayed')
            return False
        return (
            self.in_infra_vms and
            self.entities.title.text == 'VM and Instance "{}"'.format(expected_name) and
            relationship_provider_name == expected_provider)


class InfraVmTimelinesView(TimelinesView, InfraVmView):
    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        return (
            self.in_infra_vms and
            self.title.text == 'Timelines for Virtual Machine "{}"'.format(expected_name))
    # Timelines for Virtual Machine "landon-test"


class InfraVmReconfigureView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    memory = BootstrapSwitch(name='cb_memory')
    # memory set to True unlocks the following (order matters - first type then value!):
    mem_size_unit = BootstrapSelect(id='mem_type')
    mem_size = WInput(id='memory_value')

    cpu = BootstrapSwitch(name='cb_cpu')
    # cpu set to True unlocks the following:
    sockets = BootstrapSelect(id='socket_count')
    cores_per_socket = BootstrapSelect(id='cores_per_socket_count')
    cpu_total = WInput()  # read-only, TODO widgetastic

    disks_table = DisksTable()
    affected_vms = Table('.//div[@id="records_div" or @id="miq-gtl-view"]//table')

    submit_button = Button('Submit', classes=[Button.PRIMARY])
    cancel_button = Button('Cancel', classes=[Button.DEFAULT])

    @property
    def is_displayed(self):
        return (self.title.text == 'Reconfigure Virtual Machine' and
                len([row for row in self.affected_vms.rows()]) == 1 and
                self.context['object'].name in [row.name.text for row in self.affected_vms.rows()])


class InfraVmSnapshotToolbar(View):
    """The toolbar on the snapshots page"""
    history = Dropdown('History')
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    create = Button(title='Create a new snapshot for this VM')
    delete = Dropdown('Delete Snapshots')
    revert = Button(title='Revert to selected snapshot')


class InfraVmSnapshotView(InfraVmView):
    """The Snapshots page"""
    toolbar = View.nested(InfraVmSnapshotToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    title = Text('#explorer_title_text')
    description = Text('//label[normalize-space(.)="Description"]/../div/p|'
                       '//td[@class="key" and normalize-space(.)="Description"]/..'
                       '/td[not(contains(@class, "key"))]')
    tree = ManageIQTree('snapshot_treebox')

    @property
    def is_displayed(self):
        """Is this view being displayed"""
        expected_title = '"Snapshots" for Virtual Machine "{}"'.format(self.context['object'].name)
        return self.in_infra_vms and self.title.text == expected_title


class InfraVmSnapshotAddView(InfraVmView):
    """Add a snapshot"""
    title = Text('#explorer_title_text')
    name = TextInput('name')
    description = TextInput('description')
    snapshot_vm_memory = Checkbox('snap_memory')
    create = Button('Create')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        """Is this view being displayed"""
        return False


class InfraVmGenealogyToolbar(View):
    """The toolbar on the genalogy page"""
    history = Dropdown(title='History')
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    edit_tags = Button(title='Edit Tags for this VM')
    compare = Button(title='Compare selected VMs')


class InfraVmGenealogyView(InfraVmView):
    """The Genealogy page"""
    toolbar = View.nested(InfraVmGenealogyToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    title = Text('#explorer_title_text')
    tree = CheckableBootstrapTreeview('genealogy_treebox')

    @property
    def is_displayed(self):
        """Is this view being displayed"""
        expected_title = '"Genealogy" for Virtual Machine "{}"'.format(self.context['object'].name)
        return self.in_infra_vms and self.title.text == expected_title


class VMDisk(
        namedtuple('VMDisk', ['filename', 'size', 'size_unit', 'type', 'mode'])):
    """Represents a single VM disk

    Note:
        Cannot be changed once created.
    """
    EQUAL_ATTRS = {'type', 'mode', 'size_mb'}

    def __eq__(self, other):
        # If both have filename, it's easy
        if self.filename and other.filename:
            return self.filename == other.filename
        # If one of filenames is None (before disk is created), compare the rest
        for eq_attr in self.EQUAL_ATTRS:
            if getattr(self, eq_attr) != getattr(other, eq_attr):
                return False
        return True

    @property
    def size_mb(self):
        return self.size * 1024 if self.size_unit == 'GB' else self.size


class VMHardware(object):
    """Represents VM's hardware, i.e. CPU (cores, sockets) and memory
    """
    EQUAL_ATTRS = {'cores_per_socket', 'sockets', 'mem_size_mb'}

    def __init__(self, cores_per_socket=None, sockets=None, mem_size=None, mem_size_unit='MB'):
        self.cores_per_socket = cores_per_socket
        self.sockets = sockets
        self.mem_size = mem_size
        self.mem_size_unit = mem_size_unit

    def __eq__(self, other):
        for eq_attr in self.EQUAL_ATTRS:
            if getattr(self, eq_attr) != getattr(other, eq_attr):
                return False
        return True

    @property
    def mem_size_mb(self):
        return self.mem_size * 1024 if self.mem_size_unit == 'GB' else self.mem_size


class VMConfiguration(Pretty):
    """Represents VM's full configuration - hardware, disks and so forth

    Args:
        vm: VM that exists within current appliance

    Note:
        It can be only instantiated by fetching an existing VM's configuration, as it is designed
        to be used to reconfigure an existing VM.
    """
    pretty_attrs = ['hw', 'num_disks']

    def __init__(self, vm):
        self.hw = VMHardware()
        self.disks = []
        self.vm = vm
        self._load()

    def __eq__(self, other):
        return (
            (self.hw == other.hw) and (self.num_disks == other.num_disks) and
            all(disk in other.disks for disk in self.disks))

    def _load(self):
        """Loads the configuration from the VM object's appliance (through DB)
        """
        appl_db = self.vm.appliance.db.client

        # Hardware
        ems = appl_db['ext_management_systems']
        vms = appl_db['vms']
        hws = appl_db['hardwares']
        hw_data = appl_db.session.query(ems, vms, hws).filter(
            ems.name == self.vm.provider.name).filter(
            vms.ems_id == ems.id).filter(
            vms.name == self.vm.name).filter(
            hws.vm_or_template_id == vms.id
        ).first().hardwares
        self.hw = VMHardware(
            hw_data.cpu_cores_per_socket, hw_data.cpu_sockets, hw_data.memory_mb, 'MB')
        hw_id = hw_data.id

        # Disks
        disks = appl_db['disks']
        disks_data = appl_db.session.query(disks).filter(
            disks.hardware_id == hw_id).filter(
            disks.device_type == 'disk'
        ).all()
        for disk_data in disks_data:
            # In DB stored in bytes, but UI default is GB
            size_gb = disk_data.size / (1024 ** 3)
            self.disks.append(
                VMDisk(
                    filename=disk_data.filename,
                    size=size_gb,
                    size_unit='GB',
                    type=disk_data.disk_type,
                    mode=disk_data.mode
                ))

    def copy(self):
        """Returns a copy of this configuration
        """
        config = VMConfiguration.__new__(VMConfiguration)
        config.hw = copy(self.hw)
        # We can just make shallow copy here because disks can be only added or deleted, not edited
        config.disks = self.disks[:]
        config.vm = self.vm
        return config

    def add_disk(self, size, size_unit='GB', type='thin', mode='persistent'):
        """Adds a disk to the VM

        Args:
            size: Size of the disk
            size_unit: Unit of size ('MB' or 'GB')
            type: Type of the disk ('thin' or 'thick')
            mode: Mode of the disk ('persistent', 'independent_persistent' or
                  'independent_nonpersistent')

        Note:
            This method is designed to correspond with the DB, not with the UI.
            In the UI, dependency is represented by a separate Yes / No option which is _incorrect_
            design that we don't follow. Correctly, mode should be a selectbox of 3 items:
            Persistent, Independent Persistent and Independent Nonpersistent.
            Just Nonpersistent is an invalid setup that UI currently (5.8) allows.
        """
        # New disk doesn't have a filename, until actually added
        disk = VMDisk(filename=None, size=size, size_unit=size_unit, type=type, mode=mode)
        self.disks.append(disk)
        return disk

    def delete_disk(self, filename=None, index=None):
        """Removes a disk of given filename or index"""
        if filename:
            disk = [disk for disk in self.disks if disk.filename == filename][0]
            self.disks.remove(disk)
        elif index:
            del self.disks[index]
        else:
            raise TypeError("Either filename or index must be specified")

    @property
    def num_disks(self):
        return len(self.disks)

    def get_changes_to_fill(self, other_configuration):
        """ Returns changes to be applied to this config to reach the other config

        Note:
            Result of this method is used for form filling by VM's reconfigure method.
        """
        changes = {}
        changes['disks'] = []
        for key in ['cores_per_socket', 'sockets']:
            if getattr(self.hw, key) != getattr(other_configuration.hw, key):
                changes[key] = str(getattr(other_configuration.hw, key))
                changes['cpu'] = True
        if (self.hw.mem_size != other_configuration.hw.mem_size or
                self.hw.mem_size_unit != other_configuration.hw.mem_size_unit):
            changes['memory'] = True
            changes['mem_size'] = other_configuration.hw.mem_size
            changes['mem_size_unit'] = other_configuration.hw.mem_size_unit
        for disk in self.disks + other_configuration.disks:
            if disk in self.disks and disk not in other_configuration.disks:
                changes['disks'].append({'action': 'delete', 'disk': disk, 'delete_backing': None})
            elif disk not in self.disks and disk in other_configuration.disks:
                changes['disks'].append({'action': 'add', 'disk': disk})
        return changes


@attr.s
class InfraVm(VM):
    """Represents an infrastructure provider's virtual machine in CFME

    Note the args are defined at common.BaseVM|VM class
    Args:
        name: Name of the virtual machine resource
        provider: :py:class:`cfme.infrastructure.provider.InfraProvider` object
        template_name: Name of the template to use for provisioning
    """

    @attr.s
    # TODO snapshot collections
    class Snapshot(object):
        snapshot_tree = ManageIQTree('snapshot_treebox')

        name = attr.ib(default=None)
        description = attr.ib(default=None)
        memory = attr.ib(default=None)
        parent_vm = attr.ib(default=None)

        @property
        def exists(self):
            title = getattr(self, self.parent_vm.provider.SNAPSHOT_TITLE)
            view = navigate_to(self.parent_vm, 'SnapshotsAll')
            if view.tree.is_displayed:
                root_item = view.tree.expand_path(self.parent_vm.name)
                return has_child(view.tree, title, root_item)
            else:
                return False

        @property
        def active(self):
            """Check if the snapshot is active.

            Returns:
                bool: True if snapshot is active, False otherwise.
            """
            title = getattr(self, self.parent_vm.provider.SNAPSHOT_TITLE)
            view = navigate_to(self.parent_vm, 'SnapshotsAll')
            root_item = view.tree.expand_path(self.parent_vm.name)
            return has_child(view.tree, '{} (Active)'.format(title), root_item)

        def create(self, force_check_memory=False):
            """Create a snapshot"""
            view = navigate_to(self.parent_vm, 'SnapshotsAdd')
            snapshot_dict = {'description': self.description}
            if self.name is not None:
                snapshot_dict['name'] = self.name
            if (force_check_memory or
                    self.parent_vm.provider.mgmt.is_vm_running(self.parent_vm.name)):
                snapshot_dict["snapshot_vm_memory"] = self.memory
            if force_check_memory and not view.snapshot_vm_memory.is_displayed:
                raise NoSuchElementException('Snapshot VM memory checkbox not present')
            view.fill(snapshot_dict)
            view.create.click()
            view.flash.assert_no_error()
            list_view = self.parent_vm.create_view(InfraVmSnapshotView)
            wait_for(lambda: self.exists, num_sec=300, delay=20,
                     fail_func=list_view.toolbar.reload.click, handle_exception=True,
                     message="Waiting for snapshot create")

        def delete(self, cancel=False):
            title = getattr(self, self.parent_vm.provider.SNAPSHOT_TITLE)
            view = navigate_to(self.parent_vm, 'SnapshotsAll')
            root_item = view.tree.expand_path(self.parent_vm.name)
            snapshot_path = find_path(view.tree, title, root_item)
            if not snapshot_path:
                raise Exception('Could not find snapshot with name "{}"'.format(title))
            else:
                view.tree.click_path(*snapshot_path)

            view.toolbar.delete.item_select('Delete Selected Snapshot', handle_alert=not cancel)
            if not cancel:
                flash_message = version.pick({
                    version.LOWEST: "Remove Snapshot initiated for 1 "
                                    "VM and Instance from the CFME Database",
                    version.UPSTREAM: "Delete Snapshot initiated for 1 "
                                      "VM and Instance from the ManageIQ Database",
                    '5.9': "Delete Snapshot initiated for 1 VM and Instance from the CFME Database"
                })
                view.flash.assert_message(flash_message)

            wait_for(lambda: not self.exists, num_sec=300, delay=20, fail_func=view.browser.refresh,
                     message="Waiting for snapshot delete")

        def delete_all(self, cancel=False):
            view = navigate_to(self.parent_vm, 'SnapshotsAll')
            view.toolbar.delete.item_select('Delete All Existing Snapshots',
                                            handle_alert=not cancel)
            if not cancel:
                flash_message = version.pick({
                    version.LOWEST: "Remove All Snapshots initiated for 1 VM and "
                                    "Instance from the CFME Database",
                    version.UPSTREAM: "Delete All Snapshots initiated for 1 VM "
                                      "and Instance from the ManageIQ Database",
                    '5.9': "Delete All Snapshots initiated for 1 VM "
                           "and Instance from the CFME Database"})

                view.flash.assert_message(flash_message)

        def revert_to(self, cancel=False):
            title = getattr(self, self.parent_vm.provider.SNAPSHOT_TITLE)
            view = navigate_to(self.parent_vm, 'SnapshotsAll')
            root_item = view.tree.expand_path(self.parent_vm.name)
            snapshot_path = find_path(view.tree, title, root_item)
            if not snapshot_path:
                raise Exception('Could not find snapshot with name "{}"'.format(title))
            else:
                view.tree.click_path(*snapshot_path)

            view.toolbar.revert.click(handle_alert=not cancel)
            if not cancel:
                flash_message = version.pick({
                    version.LOWEST: "Revert To Snapshot initiated for 1 VM and Instance from "
                                    "the CFME Database",
                    version.UPSTREAM: "Revert to a Snapshot initiated for 1 VM and Instance "
                                      "from the ManageIQ Database",
                    '5.9': "Revert to a Snapshot initiated for 1 VM and Instance from "
                           "the CFME Database"})
                view.flash.assert_message(flash_message)

        def refresh(self):
            view = navigate_to(self.parent_vm, 'SnapshotsAll')
            view.toolbar.reload.click()

    # POWER CONTROL OPTIONS
    SUSPEND = "Suspend"
    POWER_ON = "Power On"
    POWER_OFF = "Power Off"
    GUEST_RESTART = "Restart Guest"
    GUEST_SHUTDOWN = "Shutdown Guest"
    RESET = "Reset"
    # POWER STATE
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_SUSPENDED = "suspended"

    ALL_LIST_LOCATION = "infra_vms"
    TO_OPEN_EDIT = "Edit this VM"
    TO_OPEN_RECONFIGURE = "Reconfigure this VM"
    TO_RETIRE = "Retire this VM"
    VM_TYPE = "Virtual Machine"
    DETAILS_VIEW_CLASS = InfraVmDetailsView

    def power_control_from_provider(self, option):
        """Power control a vm from the provider

        Args:
            option: power control action to take against vm

        Raises:
            OptionNotAvailable: option parm must have proper value
        """
        if option == InfraVm.POWER_ON:
            self.provider.mgmt.start_vm(self.name)
        elif option == InfraVm.POWER_OFF:
            self.provider.mgmt.stop_vm(self.name)
        elif option == InfraVm.SUSPEND:
            self.provider.mgmt.suspend_vm(self.name)
        # elif reset:
        # elif shutdown:
        else:
            raise OptionNotAvailable(option + " is not a supported action")

    def migrate_vm(self, email=None, first_name=None, last_name=None,
                   host=None, datastore=None):
        view = navigate_to(self, 'Migrate')
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
            host_name = host or prov_data.get("host")
            datastore_name = datastore or prov_data.get("datastore")
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")
        request_data = {
            'request': {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            },
            'environment': {
                'host_name': {'name': host_name}
            },
        }
        from cfme.infrastructure.provider.rhevm import RHEVMProvider
        if not self.provider.one_of(RHEVMProvider):
            request_data['environment'].update({'datastore_name': {'name': datastore_name}})
        view.form.fill_with(request_data, on_change=view.form.submit)

    def clone_vm(self, email=None, first_name=None, last_name=None,
                 vm_name=None, provision_type=None):
        view = navigate_to(self, 'Clone')
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")

        provisioning_data = {
            'catalog': {'vm_name': vm_name,
                        'provision_type': provision_type},
            'request': {
                'email': email,
                'first_name': first_name,
                'last_name': last_name},
            'environment': {"host_name": {'name': prov_data.get("host")},
                            "datastore_name": {"name": prov_data.get("datastore")}},
            'network': {'vlan': partial_match(prov_data.get("vlan"))},
        }
        view.form.fill_with(provisioning_data, on_change=view.form.submit_button)

    def publish_to_template(self, template_name, email=None, first_name=None, last_name=None):
        view = navigate_to(self, 'Publish')
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")

        provisioning_data = {
            'catalog': {'vm_name': template_name},
            'request': {
                'email': email,
                'first_name': first_name,
                'last_name': last_name},
            'environment': {"host_name": {'name': prov_data.get("host")},
                            "datastore_name": {"name": prov_data.get("datastore")}},
        }
        view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
        cells = {'Description': 'Publish from [{}] to [{}]'.format(self.name, template_name)}
        provision_request = self.appliance.collections.requests.instantiate(cells=cells)
        provision_request.wait_for_request()
        return self.appliance.collections.infra_templates.instantiate(template_name, self.provider)

    @property
    def total_snapshots(self):
        """Returns the number of snapshots for this VM. If it says ``None``, returns ``0``."""
        view = navigate_to(self, "Details")
        snapshots = view.entities.summary("Properties").get_text_of("Snapshots").strip().lower()
        if snapshots == "none":
            return 0
        else:
            return int(snapshots)

    @property
    def current_snapshot_name(self):
        """Returns the current snapshot name."""
        view = navigate_to(self, 'SnapshotsAll')
        active_snapshot = view.tree.selected_item if view.tree.is_displayed else None
        if active_snapshot:
            return active_snapshot.text.split(' (Active')[0]

    @property
    def current_snapshot_description(self):
        """Returns the current snapshot description."""
        view = navigate_to(self, 'SnapshotsAll')
        active_snapshot = view.tree.selected_item if view.tree.is_displayed else None
        if active_snapshot:
            active_snapshot.click()
            return view.description.text

    @property
    def genealogy(self):
        return Genealogy(self)

    def get_vm_via_rest(self):
        return self.appliance.rest_api.collections.vms.get(name=self.name)

    def get_collection_via_rest(self):
        return self.appliance.rest_api.collections.vms

    @property
    def cluster_id(self):
        """returns id of cluster current vm belongs to"""
        vm = self.get_vm_via_rest()
        return int(vm.ems_cluster_id)

    @attr.s
    class CfmeRelationship(object):
        vm = attr.ib()

        def navigate(self):
            return navigate_to(self.vm, 'EditManagementEngineRelationship')

        def is_relationship_set(self):
            return '<Not a Server>' not in self.get_relationship()

        def get_relationship(self):
            view = self.navigate()
            rel = str(view.form.server.all_selected_options[0])
            view.form.cancel_button.click()
            return rel

        def set_relationship(self, server_name, server_id, click_cancel=False):
            view = self.navigate()
            view.form.fill({'server': '{} ({})'.format(server_name, server_id)})

            if click_cancel:
                view.form.cancel_button.click()
            else:
                view.form.save_button.click()
                view.flash.assert_success_message('Management Engine Relationship saved')

    @property
    def configuration(self):
        return VMConfiguration(self)

    def reconfigure(self, new_configuration=None, changes=None, cancel=False):
        """Reconfigures the VM based on given configuration or set of changes

        Args:
            new_configuration: VMConfiguration object with desired configuration
            changes: Set of changes to request; alternative to new_configuration
                     See VMConfiguration.get_changes_to_fill to see expected format of the data
            cancel: `False` if we want to submit the changes, `True` otherwise
        """
        if not new_configuration and not changes:
            raise TypeError(
                "You must provide either new configuration or changes to apply.")

        if new_configuration:
            changes = self.configuration.get_changes_to_fill(new_configuration)

        any_changes = any(v not in [None, []] for v in changes.values())
        if not any_changes and not cancel:
            raise ValueError("No changes specified - cannot reconfigure VM.")

        vm_recfg = navigate_to(self, 'Reconfigure', wait_for_view=True)

        # We gotta add disks separately
        fill_data = {k: v for k, v in changes.items() if k != 'disks'}
        vm_recfg.fill(fill_data)

        # Helpers for VM Reconfigure request
        cpu_message = "Processor Sockets: {}{}".format(
            changes.get("sockets", "1"), ", Processor Cores Per Socket: {}".format(
                changes.get("cores_per_socket", "1"))) if changes.get("cpu", False) else None
        ram_message = "Memory: {} {}".format(
            changes.get("mem_size", "0"), changes.get("mem_size_unit", "MB")) if changes.get(
            "memory", False) else None
        disk_message = None

        for disk_change in changes['disks']:
            action, disk = disk_change['action'], disk_change['disk']
            if action == 'add':
                # TODO This conditional has to go, once the 'Dependent' switch is removed from UI
                if 'independent' in disk.mode:
                    mode = disk.mode.split('independent_')[1]
                    dependent = False
                else:
                    mode = disk.mode
                    dependent = True
                row = vm_recfg.disks_table.click_add_disk()
                row.type.fill(disk.type)
                # Unit first, then size (otherwise JS would try to recalculate the size...)
                from cfme.infrastructure.provider.rhevm import RHEVMProvider
                if self.provider.one_of(RHEVMProvider):
                    # TODO: Workaround necessary until BZ 1524960 is resolved
                    # -- block start --
                    row[3].fill(disk.size_unit)
                else:
                    if self.appliance.version < '5.9':
                        unit_column = 4
                    else:
                        unit_column = 5
                    # -- block end --
                    row[unit_column].fill(disk.size_unit)
                    row.mode.fill(mode)
                    row.dependent.fill(dependent)
                row.size.fill(disk.size)
                row.actions.widget.click()
                disk_message = 'Add Disks'
            elif action == 'delete':
                row = vm_recfg.disks_table.row(name=disk.filename)
                # `delete_backing` removes disk from the env
                row.delete_backing.fill(True)
                row.actions.widget.click()
                disk_message = 'Remove Disks'
            else:
                raise ValueError("Unknown disk change action; must be one of: add, delete")
        message = ", ".join(filter(None, [ram_message, cpu_message, disk_message]))
        if cancel:
            vm_recfg.cancel_button.click()
            view = self.appliance.browser.create_view(InfraVmDetailsView)
            view.flash.assert_success_message('VM Reconfigure Request was cancelled by the user')
        else:
            vm_recfg.submit_button.click()
            view = self.appliance.browser.create_view(RequestsView)
            view.flash.assert_success_message("VM Reconfigure Request was saved")
            return self.appliance.collections.requests.instantiate(description="{} - {}".format(
                self.name, message), partial_check=True)

    @property
    def cluster(self):
        all_clusters = self.provider.get_clusters()
        return next(cl for cl in all_clusters if cl.id == self.cluster_id)

    @property
    def host(self):
        vm_api = self.appliance.rest_api.collections.vms.get(name=self.name)
        vm_api.reload(attributes='host_name')
        host = self.appliance.collections.hosts.instantiate(name=vm_api.host_name,
                                                            provider=self.provider)
        return host

    @property
    def vm_default_args(self):
        """Represents dictionary used for Vm/Instance provision with mandatory default args"""
        provisioning = self.provider.data['provisioning']
        inst_args = {
            'request': {
                'email': 'vm_provision@cfmeqe.com'},
            'catalog': {
                'vm_name': self.name},
            'environment': {
                'host_name': {'name': provisioning['host']},
                'datastore_name': {'name': provisioning['datastore']}},
            'network': {
                'vlan': partial_match(provisioning['vlan'])}
        }

        return inst_args

    @property
    def vm_default_args_rest(self):
        """Represents dictionary used for REST API Vm/Instance provision with minimum required
        default args

        """
        from cfme.infrastructure.provider.rhevm import RHEVMProvider
        if not self.provider.is_refreshed():
            self.provider.refresh_provider_relationships()
            wait_for(self.provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        provisioning = self.provider.data['provisioning']
        template_name = provisioning['template']
        template = self.appliance.rest_api.collections.templates.get(name=template_name,
                                                                     ems_id=self.provider.id)
        host_id = self.appliance.rest_api.collections.hosts.get(name=provisioning['host']).id
        ds_id = self.appliance.rest_api.collections.data_stores.get(
            name=provisioning['datastore']).id
        inst_args = {
            "version": "1.1",
            "template_fields": {
                "guid": template.guid,
            },
            "vm_fields": {
                "placement_auto": False,
                "vm_name": self.name,
                "request_type": "template",
                "placement_ds_name": ds_id,
                "placement_host_name": host_id,
                "vlan": provisioning["vlan"],
            },
            "requester": {
                "user_name": "admin",
                "owner_email": "admin@cfmeqe.com",
                "auto_approve": True,
            },
            "tags": {
            },
            "additional_values": {
            },
            "ems_custom_attributes": {
            },
            "miq_custom_attributes": {
            }
        }

        if self.provider.one_of(RHEVMProvider):
            inst_args['vm_fields']['provision_type'] = 'native_clone'
            cluster_id = self.appliance.rest_api.collections.clusters.get(name='Default').id
            inst_args['vm_fields']['placement_cluster_name'] = cluster_id
            # TODO Workaround for BZ 1541036/1449157. <Template> uses template vnic_profile
            # shouldn't be default
            if self.appliance.version > '5.9.0.16':
                inst_args['vm_fields']['vlan'] = '<Template>'

        return inst_args


@attr.s
class InfraVmCollection(VMCollection):
    ENTITY = InfraVm

    def all(self):
        """Return entities for all items in collection"""
        # provider filter means we're viewing vms through provider details relationships
        # provider filtered 'All' view includes vms and templates, can't be used
        provider = self.filters.get('provider')  # None if no filter, need for entity instantiation
        view = navigate_to(provider or self,
                           'ProviderVms' if provider else 'VMsOnly')
        # iterate pages here instead of use surf_pages=True because data is needed
        entities = []
        for _ in view.entities.paginator.pages():  # auto-resets to first page
            page_entities = [entity for entity in view.entities.get_all(surf_pages=False)]
            entities.extend(
                # when provider filtered view, there's no provider data value
                [self.instantiate(e.data['name'], provider or get_crud_by_name(e.data['provider']))
                 for e in page_entities
                 if e.data.get('provider') != '']  # safe provider check, orphaned shows no provider
            )
        return entities


@attr.s
class InfraTemplate(Template):
    REMOVE_MULTI = "Remove Templates from the VMDB"
    VM_TYPE = "Template"

    @property
    def genealogy(self):
        return Genealogy(self)


@attr.s
class InfraTemplateCollection(TemplateCollection):
    ENTITY = InfraTemplate

    def all(self):
        """Return entities for all items in collection"""
        # provider filter means we're viewing templates through provider details relationships
        # provider filtered 'All' view includes vms and templates, can't be used
        provider = self.filters.get('provider')  # None if no filter, need for entity instantiation
        view = navigate_to(provider or self,
                           'ProviderTemplates' if provider else 'TemplatesOnly')
        # iterate pages here instead of use surf_pages=True because data is needed
        entities = []
        for _ in view.entities.paginator.pages():  # auto-resets to first page
            page_entities = [entity for entity in view.entities.get_all(surf_pages=False)]
            entities.extend(
                # when provider filtered view, there's no provider data value
                [self.instantiate(e.data['name'], provider or get_crud_by_name(e.data['provider']))
                 for e in page_entities
                 if e.data.get('provider') != '']  # safe provider check, orphaned shows no provider
            )
        return entities


@attr.s
class Genealogy(object):
    """Class, representing genealogy of an infra object with possibility of data retrieval
    and comparison.

    Args:
        o: The :py:class:`InfraVm` or :py:class:`Template` object.
    """
    mode_mapping = {
        'exists': 'Exists Mode',
        'details': 'Details Mode',
    }

    attr_mapping = {
        'all': 'All Attributes',
        'different': 'Attributes with different values',
        'same': 'Attributes with same values',
    }

    obj = attr.ib()

    def navigate(self):
        return navigate_to(self.obj, 'GenealogyAll')

    def compare(self, *objects, **kwargs):
        """Compares two or more objects in the genealogy.

        Args:
            *objects: :py:class:`InfraVm` or :py:class:`Template` or :py:class:`str` with name.

        Keywords:
            sections: Which sections to compare.
            attributes: `all`, `different` or `same`. Default: `all`.
            mode: `exists` or `details`. Default: `exists`."""
        sections = kwargs.get('sections')
        attributes = kwargs.get('attributes', 'all').lower()
        mode = kwargs.get('mode', 'exists').lower()
        assert len(objects) >= 2, 'You must specify at least two objects'
        objects = map(lambda o: o.name if isinstance(o, (InfraVm, InfraTemplate)) else o, objects)
        view = self.navigate()
        for obj in objects:
            if not isinstance(obj, list):
                path = find_path(view.tree, obj)
            view.tree.check_node(*path)
        view.toolbar.compare.click()
        view.flash.assert_no_errors()
        # COMPARE PAGE
        compare_view = self.obj.create_view('Compare')
        if sections is not None:
            map(lambda path: compare_view.tree.check_node(*path), sections)
            compare_view.apply.click()
            compare_view.flash.assert_no_errors()
        # Set requested attributes sets
        getattr(compare_view.toolbar, self.attr_mapping[attributes]).click()
        # Set the requested mode
        getattr(compare_view.toolbar, self.mode_mapping[mode]).click()

    @property
    def tree(self):
        """Returns contents of the tree with genealogy"""
        view = self.navigate()
        return view.tree.read_contents()

    @property
    def ancestors(self):
        """Returns list of ancestors of the represented object."""
        view = self.navigate()
        path = find_path(view.tree, '(Selected)')
        if not path:
            raise ValueError("Something wrong happened, path not found!")
        processed_path = []
        for step in path[:-1]:
            # We will remove the (parent) and (Selected) suffixes
            processed_path.append(re.sub(r"\s*(?:\(Current\)|\(Parent\))$", "", step))
        return processed_path


@navigator.register(Template, 'All')
@navigator.register(InfraVm, 'All')
@navigator.register(InfraTemplateCollection, 'All')
@navigator.register(InfraVmCollection, 'All')
class VmAllWithTemplates(CFMENavigateStep):
    VIEW = VmsTemplatesAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Virtual Machines')
        self.view.sidebar.vmstemplates.tree.click_path('All VMs & Templates')

    def resetter(self, *args, **kwargs):
        if self.view.pagination.is_displayed:
            self.view.pagination.set_items_per_page(1000)
        self.view.reset_page()


@navigator.register(InfraTemplateCollection, 'AllForProvider')
@navigator.register(InfraTemplate, 'AllForProvider')
@navigator.register(InfraVmCollection, 'AllForProvider')
@navigator.register(InfraVm, 'AllForProvider')
class VmAllWithTemplatesForProvider(CFMENavigateStep):
    VIEW = VmTemplatesAllForProviderView

    def prerequisite(self):
        view = None
        try:
            view = navigate_to(self.obj, 'All')
        except NavigationDestinationNotFound:
            view = navigate_to(self.obj.parent, 'All')
        finally:
            if view is None:
                raise NavigationDestinationNotFound('No view set during prerequisite: '
                                                    'nav: {}, obj: {}'
                                                    .format(self, self.obj))

    def step(self, *args, **kwargs):
        # provider has been passed, TODO remove this usage
        if 'provider' in kwargs:
            provider_name = kwargs['provider'].name
        # the collection is navigation target, use its filter value
        elif (isinstance(self.obj, (InfraTemplateCollection, InfraVmCollection)) and
                self.obj.filters.get('provider')):
            provider_name = self.obj.filters['provider'].name
        elif isinstance(self.obj, (InfraTemplate, InfraVm)):
            provider_name = self.obj.provider.name
        else:
            raise DestinationNotFound("Unable to identify a provider for AllForProvider navigation")
        self.view.sidebar.vmstemplates.tree.click_path('All VMs & Templates', provider_name)

    def resetter(self, *args, **kwargs):
        self.view.reset_page()


@navigator.register(InfraTemplate, 'Details')
@navigator.register(InfraVm, 'Details')
class VmAllWithTemplatesDetails(CFMENavigateStep):
    VIEW = InfraVmDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        try:
            entity_item = self.prerequisite_view.entities.get_entity(
                name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise VmOrInstanceNotFound('Failed to locate VM/Template with name "{}"'.
                                       format(self.obj.name))
        entity_item.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(InfraTemplate, 'ArchiveDetails')
@navigator.register(InfraVm, 'ArchiveDetails')
class ArchiveDetails(CFMENavigateStep):
    VIEW = InfraVmDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            entity_item = self.prerequisite_view.entities.get_entity(
                name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise VmOrInstanceNotFound('Failed to locate VM/Template with name "{}"'.
                                       format(self.obj.name))
        entity_item.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(InfraTemplate, 'AnyProviderDetails')
@navigator.register(InfraVm, 'AnyProviderDetails')
class VmAllWithTemplatesDetailsAnyProvider(VmAllWithTemplatesDetails):
    """
    Page with details for VM or template.
    This is required in case you want to get details about archived/orphaned VM/template.
    In such case, you cannot get to the detail page by navigating from list of VMs for a provider
    since archived/orphaned VMs has lost its relationship with the original provider.
    """
    prerequisite = NavigateToSibling('All')


@navigator.register(InfraVmCollection, 'VMsOnly')
class VmAll(CFMENavigateStep):
    VIEW = VmsOnlyAllView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        if 'filter_folder' not in kwargs:
            self.view.sidebar.vms.tree.click_path('All VMs')
        elif 'filter_folder' in kwargs and 'filter_name' in kwargs:
            self.view.sidebar.vms.tree.click_path('All VMs', kwargs['filter_folder'],
            kwargs['filter_name'])
        else:
            raise DestinationNotFound("the destination isn't found")

    def resetter(self, *args, **kwargs):
        self.view.reset_page()


@navigator.register(InfraVm, 'VMsOnlyDetails')
class VmDetails(CFMENavigateStep):
    VIEW = InfraVmDetailsView

    def prerequisite(self):
        view = None
        try:
            view = navigate_to(self.obj, 'VMsOnly')
        except NavigationDestinationNotFound:
            view = navigate_to(self.obj.parent, 'VMsOnly')
        finally:
            if view is None:
                raise NavigationDestinationNotFound('No view set during prerequisite')
        return view

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                             surf_pages=True)
        except ItemNotFound:
            raise VmOrInstanceNotFound('Failed to locate VM/Template with name "{}"'.
                                       format(self.obj.name))
        row.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(InfraVm, 'SnapshotsAll')
class VmSnapshotsAll(CFMENavigateStep):
    VIEW = InfraVmSnapshotView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary('Properties').click_at('Snapshots')


@navigator.register(InfraVm, 'SnapshotsAdd')
class VmSnapshotsAdd(CFMENavigateStep):
    VIEW = InfraVmSnapshotAddView
    prerequisite = NavigateToSibling('SnapshotsAll')

    def step(self, *args, **kwargs):
        if self.prerequisite_view.tree.is_displayed:
            self.prerequisite_view.tree.click_path(self.obj.name)
        self.prerequisite_view.toolbar.create.click()


@navigator.register(InfraTemplate, 'GenealogyAll')
@navigator.register(InfraVm, 'GenealogyAll')
class VmGenealogyAll(CFMENavigateStep):
    VIEW = InfraVmGenealogyView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary('Relationships').click_at('Genealogy')


@navigator.register(InfraVm, 'Migrate')
class VmMigrate(CFMENavigateStep):
    VIEW = MigrateVmView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Migrate this VM")


@navigator.register(InfraVm, 'Publish')
class VmPublish(CFMENavigateStep):
    VIEW = PublishVmView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.lifecycle.item_select("Publish this VM to a Template")


@navigator.register(InfraVm, 'Clone')
class VmClone(CFMENavigateStep):
    VIEW = CloneVmView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Clone this VM")


@navigator.register(InfraVm, 'SetRetirement')
class SetRetirement(CFMENavigateStep):
    def view_classes(self):
        return VersionPick({
            Version.lowest(): RetirementView,
            "5.9": RetirementViewWithOffset
        })

    @property
    def VIEW(self):  # noqa
        return self.view_classes().pick(self.obj.appliance.version)
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Set Retirement Date')


@navigator.register(InfraTemplateCollection, 'TemplatesOnly')
class TemplatesAll(CFMENavigateStep):
    VIEW = TemplatesOnlyAllView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        if 'filter_folder' not in kwargs:
            self.view.sidebar.templates.tree.click_path('All Templates')
        elif 'filter_folder' in kwargs and 'filter_name' in kwargs:
            self.view.sidebar.templates.tree.click_path('All Templates', kwargs['filter_folder'],
                                                        kwargs['filter_name'])
        else:
            raise DestinationNotFound("the destination isn't found")


@navigator.register(InfraVmCollection, 'Provision')
class ProvisionVM(CFMENavigateStep):
    VIEW = ProvisionView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Provision VMs')


@navigator.register(InfraVm, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = InfraVmTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(InfraVm, 'Reconfigure')
class VmReconfigure(CFMENavigateStep):
    VIEW = InfraVmReconfigureView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Reconfigure this VM')


@navigator.register(InfraVm, 'Edit')
class VmEdit(CFMENavigateStep):
    VIEW = EditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this VM')


@navigator.register(InfraVm, 'EditManagementEngineRelationship')
class VmEngineRelationship(CFMENavigateStep):
    VIEW = ManagementEngineView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Edit Management Engine Relationship')


@navigator.register(InfraTemplate, 'SetOwnership')
@navigator.register(InfraVm, 'SetOwnership')
class SetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(InfraVm, 'candu')
class VmUtilization(CFMENavigateStep):
    @property
    def VIEW(self):     # noqa
        return self.obj.provider.vm_utilization_view

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
