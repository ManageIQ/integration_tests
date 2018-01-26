# -*- coding: utf-8 -*-
"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""
from collections import namedtuple
from copy import copy

import fauxfactory
import re
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.utils import partial_match, Parameter, VersionPick, Version
from widgetastic.widget import (
    Text, View, TextInput, Checkbox, NoSuchElementException, ParametrizedView)
from widgetastic_patternfly import (
    Button, BootstrapSelect, BootstrapSwitch, Dropdown, Input as WInput)

from cfme.base.login import BaseLoggedInPage
from cfme.common.vm import VM, Template as BaseTemplate
from cfme.common.vm_views import (
    ManagementEngineView, CloneVmView, MigrateVmView, ProvisionView, EditView, RetirementView,
    RetirementViewWithOffset, VMDetailsEntities, VMToolbar, VMEntities, SetOwnershipView)
from cfme.exceptions import (
    VmNotFound, OptionNotAvailable, DestinationNotFound, ItemNotFound,
    VmOrInstanceNotFound)
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (
    Accordion, ConditionalSwitchableView, ManageIQTree, CheckableManageIQTree, NonJSPaginationPane,
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
        return (
            self.in_infra_vms and
            str(self.entities.title.text) ==
            'VM or Templates under Provider \"{}\"'.format(self.context['object'].provider.name))

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
        msg = '{} (All Miq Templates)'.format(self.context['object'].name)
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
            title = "{} (All Miq Templates)".format(self.context["object"].name)
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

    @toolbar.register(lambda title: "VM and Instance" in title)
    class VmsToolbar(InfraVmDetailsToolbar):
        pass

    @toolbar.register(lambda title: "VM Template and Image" in title)
    class TemplatesToolbar(InfraGenericDetailsToolbar):
        pass

    sidebar = View.nested(VmsTemplatesAccordion)
    entities = View.nested(InfraVmSummaryView)

    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        expected_provider = self.context['object'].provider.name
        try:
            relationship_provider_name = self.entities.relationships.get_text_of('Infrastructure '
                                                                                 'Provider')
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
    history = Dropdown('history')
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
        return False


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
    history = Dropdown(title='history')
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    edit_tags = Button(title='Edit Tags for this VM')
    compare = Button(title='Compare selected VMs')


class InfraVmGenealogyView(InfraVmView):
    """The Genealogy page"""
    toolbar = View.nested(InfraVmGenealogyToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    title = Text('#explorer_title_text')
    tree = CheckableManageIQTree('genealogy_treebox')

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
        for attr in self.EQUAL_ATTRS:
            if getattr(self, attr) != getattr(other, attr):
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
        for attr in self.EQUAL_ATTRS:
            if getattr(self, attr) != getattr(other, attr):
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
        disk = VMDisk(
            filename=None, size=size, size_unit=size_unit, type=type, mode=mode)
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


class Vm(VM):
    """Represents a VM in CFME

    Args:
        name: Name of the VM
        provider_crud: :py:class:`cfme.cloud.provider.Provider` object
        template_name: Name of the template to use for provisioning
    """

    class Snapshot(object):
        snapshot_tree = ManageIQTree('snapshot_treebox')

        def __init__(self, name=None, description=None, memory=None, parent_vm=None):
            super(Vm.Snapshot, self).__init__()
            self.name = name
            self.description = description
            self.memory = memory
            self.vm = parent_vm

        @property
        def exists(self):
            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            view = navigate_to(self.vm, 'SnapshotsAll')
            if view.tree.is_displayed:
                root_item = view.tree.expand_path(self.vm.name)
                return has_child(view.tree, title, root_item)
            else:
                return False

        @property
        def active(self):
            """Check if the snapshot is active.

            Returns:
                bool: True if snapshot is active, False otherwise.
            """
            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            view = navigate_to(self.vm, 'SnapshotsAll')
            root_item = view.tree.expand_path(self.vm.name)
            return has_child(view.tree, '{} (Active)'.format(title), root_item)

        def create(self, force_check_memory=False):
            """Create a snapshot"""
            view = navigate_to(self.vm, 'SnapshotsAdd')
            snapshot_dict = {
                'description': self.description
            }
            if self.name is not None:
                snapshot_dict['name'] = self.name
            if force_check_memory or self.vm.provider.mgmt.is_vm_running(self.vm.name):
                snapshot_dict["snapshot_vm_memory"] = self.memory
            view.fill(snapshot_dict)
            view.create.click()
            list_view = self.vm.create_view(InfraVmSnapshotView)
            wait_for(lambda: self.exists, num_sec=300, delay=20,
                     fail_func=list_view.toolbar.reload.click, handle_exception=True)

        def delete(self, cancel=False):
            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            view = navigate_to(self.vm, 'SnapshotsAll')
            root_item = view.tree.expand_path(self.vm.name)
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

            wait_for(lambda: not self.exists, num_sec=300, delay=20, fail_func=view.browser.refresh)

        def delete_all(self, cancel=False):
            view = navigate_to(self.vm, 'SnapshotsAll')
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
            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            view = navigate_to(self.vm, 'SnapshotsAll')
            root_item = view.tree.expand_path(self.vm.name)
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
            view = navigate_to(self.vm, 'SnapshotsAll')
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
        if option == Vm.POWER_ON:
            self.provider.mgmt.start_vm(self.name)
        elif option == Vm.POWER_OFF:
            self.provider.mgmt.stop_vm(self.name)
        elif option == Vm.SUSPEND:
            self.provider.mgmt.suspend_vm(self.name)
        # elif reset:
        # elif shutdown:
        else:
            raise OptionNotAvailable(option + " is not a supported action")

    def migrate_vm(self, email=None, first_name=None, last_name=None,
                   host_name=None, datastore_name=None):
        view = navigate_to(self, 'Migrate')
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")
        provisioning_data = {
            'request': {
                'email': email,
                'first_name': first_name,
                'last_name': last_name},
            'environment': {"host_name": {'name': prov_data.get("host")}},
        }
        if not self.provider.one_of(RHEVMProvider):
            provisioning_data['environment']["datastore_name"] = {
                "name": prov_data.get("datastore")}
        view.form.fill_with(provisioning_data, on_change=view.form.submit)

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
        view = navigate_to(self, 'Details', use_resetter=False)
        view.toolbar.lifecycle.item_select("Publish this VM to a Template")
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
        return Template(template_name, self.provider)

    @property
    def total_snapshots(self):
        """Returns the number of snapshots for this VM. If it says ``None``, returns ``0``."""
        snapshots = self.get_detail(properties=("Properties", "Snapshots")).strip().lower()
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

    class CfmeRelationship(object):

        def __init__(self, vm):
            self.vm = vm

        def navigate(self):
            return navigate_to(self.vm, 'EditManagementEngineRelationship')

        def is_relationship_set(self):
            return '<Not a Server>' not in self.get_relationship()

        def get_relationship(self):
            view = self.navigate()
            rel = str(view.form.server.all_selected_options[0].text)
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
        fill_data = {k: v for k, v in changes.iteritems() if k != 'disks'}
        vm_recfg.fill(fill_data)

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
                if self.provider.one_of(RHEVMProvider):
                    # Workaround necessary until BZ 1524960 is resolved
                    row[3].fill(disk.size_unit)
                else:
                    row[4].fill(disk.size_unit)
                    row.mode.fill(mode)
                    row.dependent.fill(dependent)
                row.size.fill(disk.size)
                row.actions.widget.click()
            elif action == 'delete':
                row = vm_recfg.disks_table.row(name=disk.filename)
                row.delete_backing.fill(disk_change['delete_backing'])
                row.actions.widget.click()
            else:
                raise ValueError("Unknown disk change action; must be one of: add, delete")

        if cancel:
            vm_recfg.cancel_button.click()
            # TODO Cannot use VM list view for flash messages here because we don't have one yet
            vm_recfg.flash.assert_no_error()
            vm_recfg.flash.assert_message('VM Reconfigure Request was cancelled by the user')
        else:
            vm_recfg.submit_button.click()
            # TODO Cannot use Requests view for flash messages here because we don't have one yet
            vm_recfg.flash.assert_no_error()
            vm_recfg.flash.assert_message("VM Reconfigure Request was saved")

        # TODO This should (one day) return a VM reconfigure request obj that we can further use

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


class Template(BaseTemplate):
    REMOVE_MULTI = "Remove Templates from the VMDB"

    @property
    def genealogy(self):
        return Genealogy(self)


class Genealogy(object):
    """Class, representing genealogy of an infra object with possibility of data retrieval
    and comparison.

    Args:
        o: The :py:class:`Vm` or :py:class:`Template` object.
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

    def __init__(self, obj):
        self.obj = obj

    def navigate(self):
        return navigate_to(self.obj, 'GenealogyAll')

    def compare(self, *objects, **kwargs):
        """Compares two or more objects in the genealogy.

        Args:
            *objects: :py:class:`Vm` or :py:class:`Template` or :py:class:`str` with name.

        Keywords:
            sections: Which sections to compare.
            attributes: `all`, `different` or `same`. Default: `all`.
            mode: `exists` or `details`. Default: `exists`."""
        sections = kwargs.get('sections')
        attributes = kwargs.get('attributes', 'all').lower()
        mode = kwargs.get('mode', 'exists').lower()
        assert len(objects) >= 2, 'You must specify at least two objects'
        objects = map(lambda o: o.name if isinstance(o, (Vm, Template)) else o, objects)
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


###
# Multi-object functions
#
# todo: to check and probably remove this function. it might be better off refactoring whole file
# todo: there will be an entity's method to apply some operation to a bunch of entities
def _method_setup(vm_names, provider_crud=None):
    """ Reduces some redundant code shared between methods """
    if isinstance(vm_names, basestring):                                 # noqa
        vm_names = [vm_names]

    if provider_crud:
        provider_crud.load_all_provider_vms()
        from cfme.utils.appliance import get_or_create_current_appliance
        app = get_or_create_current_appliance()
        view = app.browser.create_view(navigator.get_class(Vm, 'VMsOnly').VIEW)
    else:
        view = navigate_to(Vm, 'VMsOnly')

    if view.entities.paginator.exists:
        view.entities.paginator.set_items_per_page(1000)
    for vm_name in vm_names:
        view.entities.get_entity(name=vm_name).check()
    return view


def find_quadicon(vm_name):
    """Find and return a quadicon belonging to a specific vm

    Args:
        vm: vm name as displayed at the quadicon
    Returns: entity of appropriate class
    """
    # todo: VMs have such method, so, this function is good candidate for removal
    view = navigate_to(Vm, 'VMsOnly')
    try:
        return view.entites.get_entity(name=vm_name, surf_pages=True)
    except ItemNotFound:
        raise VmNotFound("VM '{}' not found in UI!".format(vm_name))


def remove(vm_names, cancel=True, provider_crud=None):
    """Removes multiple VMs from CFME VMDB

    Args:
        vm_names: List of VMs to interact with
        cancel: Whether to cancel the deletion, defaults to True
        provider_crud: provider object where vm resides on (optional)
    """
    view = _method_setup(vm_names, provider_crud)
    view.toolbar.configuration.item_select('Remove selected items from the VMDB',
                                           handle_alert=not cancel)


def wait_for_vm_state_change(vm_name, desired_state, timeout=300, provider_crud=None):
    """Wait for VM to come to desired state.

    This function waits just the needed amount of time thanks to wait_for.

    Args:
        vm_name: Displayed name of the VM
        desired_state: 'on' or 'off'
        timeout: Specify amount of time (in seconds) to wait until TimedOutError is raised
        provider_crud: provider object where vm resides on (optional)
    """
    def _looking_for_state_change(view, entity):
        view.toolbar.reload()
        return 'currentstate-' + desired_state in entity.data['state']

    view = navigate_to(Vm, 'VMsOnly')
    entity = view.entites.get_entity(name=vm_name, surf_pages=True)
    return wait_for(_looking_for_state_change, func_args=[view, entity], num_sec=timeout)


def is_pwr_option_visible(vm_names, option, provider_crud=None):
    """Returns whether a particular power option is visible.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed, only one VM can
            be passed in the list.
        option: Power option param.
        provider_crud: provider object where vm resides on (optional)
    """
    view = _method_setup(vm_names, provider_crud)
    try:
        view.toolbar.power.item_element(option)
        return True
    except NoSuchElementException:
        return False


def is_pwr_option_enabled(vm_names, option, provider_crud=None):
    """Returns whether a particular power option is enabled.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        option: Power option param.

    Raises:
        NoOptionAvailable:
            When unable to find the power option passed
    """
    view = _method_setup(vm_names, provider_crud)
    try:
        return view.toolbar.power.item_enabled(option)
    except NoSuchElementException:
        raise OptionNotAvailable("No such power option (" + str(option) + ") is available")


def do_power_control(vm_names, option, provider_crud=None, cancel=True):
    """Executes a power option against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        option: Power option param.
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the power control action
    """
    view = _method_setup(vm_names, provider_crud)

    if (is_pwr_option_visible(vm_names, provider_crud=provider_crud, option=option) and
            is_pwr_option_enabled(vm_names, provider_crud=provider_crud, option=option)):
                view.toolbar.power.item_select(option, handle_alert=not cancel)


def perform_smartstate_analysis(vm_names, provider_crud=None, cancel=True):
    """Executes a refresh relationships action against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the refresh relationships action
    """
    view = _method_setup(vm_names, provider_crud)
    view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=not cancel)


def get_all_vms(do_not_navigate=False):
    """Returns list of all vms on current page"""
    if do_not_navigate:
        from cfme.utils.appliance import get_or_create_current_appliance
        app = get_or_create_current_appliance()
        view = app.browser.create_view(navigator.get_class(Vm, 'VMsOnly').VIEW)
    else:
        view = navigate_to(Vm, 'VMsOnly')

    return [entity.name for entity in view.entities.get_all()]


def get_number_of_vms(do_not_navigate=False):
    """
    Returns the total number of VMs visible to the user,
    including those archived or orphaned
    """
    logger.info('Getting number of vms')
    if not do_not_navigate:
        view = navigate_to(Vm, 'VMsOnly')
    else:
        from cfme.utils.appliance import get_or_create_current_appliance
        app = get_or_create_current_appliance()
        view = app.browser.create_view(navigator.get_class(Vm, 'VMsOnly').VIEW)
    if not view.entities.paginator.page_controls_exist():
        logger.debug('No page controls')
        return 0
    total = view.entities.paginator.rec_total()
    logger.debug('Number of VMs: %s', total)
    return int(total)


@navigator.register(Template, 'All')
@navigator.register(Vm, 'All')
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


@navigator.register(Template, 'AllForProvider')
@navigator.register(Vm, 'AllForProvider')
class VmAllWithTemplatesForProvider(CFMENavigateStep):
    VIEW = VmTemplatesAllForProviderView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        if 'provider' in kwargs:
            provider = kwargs['provider'].name
        elif self.obj.provider:
            provider = self.obj.provider.name
        else:
            raise DestinationNotFound("the destination isn't found")
        self.view.sidebar.vmstemplates.tree.click_path('All VMs & Templates', provider)

    def resetter(self, *args, **kwargs):
        self.view.reset_page()


@navigator.register(Template, 'Details')
@navigator.register(Vm, 'Details')
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


@navigator.register(Template, 'ArchiveDetails')
@navigator.register(Vm, 'ArchiveDetails')
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


@navigator.register(Template, 'AnyProviderDetails')
@navigator.register(Vm, 'AnyProviderDetails')
class VmAllWithTemplatesDetailsAnyProvider(VmAllWithTemplatesDetails):
    """
    Page with details for VM or template.
    This is required in case you want to get details about archived/orphaned VM/template.
    In such case, you cannot get to the detail page by navigating from list of VMs for a provider
    since archived/orphaned VMs has lost its relationship with the original provider.
    """
    prerequisite = NavigateToSibling('All')


@navigator.register(Vm, 'VMsOnly')
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


@navigator.register(Vm, 'VMsOnlyDetails')
class VmDetails(CFMENavigateStep):
    VIEW = InfraVmDetailsView
    prerequisite = NavigateToSibling('VMsOnly')

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


@navigator.register(Vm, 'SnapshotsAll')
class VmSnapshotsAll(CFMENavigateStep):
    VIEW = InfraVmSnapshotView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.properties.click_at('Snapshots')


@navigator.register(Vm, 'SnapshotsAdd')
class VmSnapshotsAdd(CFMENavigateStep):
    VIEW = InfraVmSnapshotAddView
    prerequisite = NavigateToSibling('SnapshotsAll')

    def step(self, *args, **kwargs):
        if self.prerequisite_view.tree.is_displayed:
            self.prerequisite_view.tree.click_path(self.obj.name)
        self.prerequisite_view.toolbar.create.click()


@navigator.register(Template, 'GenealogyAll')
@navigator.register(Vm, 'GenealogyAll')
class VmGenealogyAll(CFMENavigateStep):
    VIEW = InfraVmGenealogyView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.relationships.click_at('Genealogy')


@navigator.register(Vm, 'Migrate')
class VmMigrate(CFMENavigateStep):
    VIEW = MigrateVmView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Migrate this VM")


@navigator.register(Vm, 'Clone')
class VmClone(CFMENavigateStep):
    VIEW = CloneVmView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Clone this VM")


@navigator.register(Vm, 'SetRetirement')
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


@navigator.register(Template, 'TemplatesOnly')
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


@navigator.register(Vm, 'Provision')
class ProvisionVM(CFMENavigateStep):
    VIEW = ProvisionView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Provision VMs')


@navigator.register(Vm, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = InfraVmTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Vm, 'Reconfigure')
class VmReconfigure(CFMENavigateStep):
    VIEW = InfraVmReconfigureView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Reconfigure this VM')


@navigator.register(Vm, 'Edit')
class VmEdit(CFMENavigateStep):
    VIEW = EditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this VM')


@navigator.register(Vm, 'EditManagementEngineRelationship')
class VmEngineRelationship(CFMENavigateStep):
    VIEW = ManagementEngineView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Edit Management Engine Relationship')


@navigator.register(Template, 'SetOwnership')
@navigator.register(Vm, 'SetOwnership')
class SetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')
