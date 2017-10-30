# -*- coding: utf-8 -*-
"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""
from copy import copy
from collections import namedtuple
import fauxfactory
from functools import partial
import re
from selenium.common.exceptions import NoSuchElementException

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import (
    Button, BootstrapSelect, BootstrapSwitch, Dropdown, Input as WInput, Tab)
from widgetastic_manageiq import (
    Accordion, ConditionalSwitchableView, ManageIQTree,
    NonJSPaginationPane, SummaryTable, TimelinesView)
from widgetastic_manageiq.vm_reconfigure import DisksTable

from cfme.base.login import BaseLoggedInPage
from cfme.common.vm import VM, Template as BaseTemplate
from cfme.common.vm_views import (
    ManagementEngineView, ProvisionView, EditView, RetirementView, VMDetailsEntities, VMToolbar,
    VMEntities)
from cfme.exceptions import (
    CandidateNotFound, VmNotFound, OptionNotAvailable, DestinationNotFound, ItemNotFound,
    VmOrInstanceNotFound)
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.web_ui import (
    CheckboxTree, Form, InfoBlock, Region, Tree, fill, flash, form_buttons,
    match_location, Table, toolbar, Calendar, Select, Input, CheckboxTable,
    summary_title, BootstrapTreeview, AngularSelect)
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for
from cfme.utils import version, deferred_verpick


# for provider specific vm/template page
QUADICON_TITLE_LOCATOR = ("//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_infra/x_show')"
                          " or contains(@href, '/show/')]")

cfg_btn = partial(toolbar.select, 'Configuration')
pol_btn = partial(toolbar.select, 'Policy')
lcl_btn = partial(toolbar.select, 'Lifecycle')
mon_btn = partial(toolbar.select, 'Monitoring')
pwr_btn = partial(toolbar.select, 'Power')

create_button = form_buttons.FormButton("Create")

manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")


manage_policies_page = Region(
    locators={
        'save_button': form_buttons.save,
    })


template_select_form = Form(
    fields=[
        ('template_table', Table('//div[@id="pre_prov_div"]//table')),
        ('cancel_button', form_buttons.cancel)
    ]
)


snapshot_form = Form(
    fields=[
        ('name', Input('name')),
        ('description', Input('description')),
        ('snapshot_memory', Input('snap_memory')),
        ('create_button', create_button),
        ('cancel_button', form_buttons.cancel)
    ])


retirement_date_form = Form(fields=[
    ('retirement_date_text', Calendar("miq_date_1")),
    ('retirement_warning_select', Select("//select[@id='retirement_warn']"))
])

retire_remove_button = "//span[@id='remove_button']/a/img"

match_page = partial(match_location, controller='vm_infra', title='Virtual Machines')


drift_table = CheckboxTable("//th[normalize-space(.)='Timestamp']/ancestor::table[1]")


class InfraGenericDetailsToolbar(View):
    reload = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown("Monitoring")
    download = Button(title='Download summary in PDF format')
    lifecycle = Dropdown('Lifecycle')


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
            self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                   'Virtual Machines'] and
            match_location(controller='vm_infra', title='Virtual Machines'))


class VmsTemplatesAllView(InfraVmView):
    """
    The collection page for instances
    """
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)
    pagination = View.nested(NonJSPaginationPane)

    @property
    def is_displayed(self):
        return (
            self.in_infra_vms and
            self.sidebar.vmstemplates.tree.currently_selected == 'All VMs & Templates' and
            self.entities.title.text == 'All VMs & Templates')

    def reset_page(self):
        self.entities.search.clear_search()


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
        self.entities.search.clear_search()


class VmsOnlyAllView(InfraVmView):
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_infra_vms and
            self.sidebar.vms.tree.currently_selected == 'All VMs' and
            self.entities.title.text == 'All VMs')

    def reset_page(self):
        self.entities.search.clear_search()


class TemplatesOnlyAllView(InfraVmView):
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(VmsTemplatesAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_infra_vms and
            self.sidebar.templates.tree.currently_selected == 'All Templates' and
            self.entities.title.text == 'All Templates')


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


class InfraVmTimelinesView(TimelinesView, BaseLoggedInPage):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                   '/vm_infra/explorer'] and
            super(TimelinesView, self).is_displayed)


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

    submit_button = Button('Submit', classes=[Button.PRIMARY])
    cancel_button = Button('Cancel', classes=[Button.DEFAULT])

    # The page doesn't contain enough info to ensure that it's the right VM -> always navigate
    is_displayed = False


class MigrateView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @View.nested
    class form(View):  # noqa
        submit = Button('Submit')
        cancel = Button('Cancel')

        @View.nested
        class request(Tab):  # noqa
            TAB_NAME = 'Request'
            email = WInput(name='requester__owner_email')
            first_name = WInput(name='requester__owner_first_name')
            last_name = WInput(name='requester__owner_last_name')
            notes = WInput(name='requester__request_notes')
            manager_name = WInput(name='requester__owner_manager')

        @View.nested
        class environment(Tab):  # noqa
            TAB_NAME = 'Environment'
            # Infra
            datacenter = BootstrapSelect('environment__placement_dc_name')
            cluster = BootstrapSelect('environment__placement_cluster_name')
            resource_pool = BootstrapSelect('environment__placement_rp_name')
            folder = BootstrapSelect('environment__placement_folder_name')
            host_filter = BootstrapSelect('environment__host_filter')
            host_name = Table('//div[@id="prov_host_div"]/table')
            datastore_filter = BootstrapSelect('environment__ds_filter')
            datastore_name = Table('//div[@id="prov_ds_div"]/table')

        @View.nested
        class schedule(Tab):  # noqa
            TAB_NAME = 'Schedule'
            # TODO radio widget #
            # schedule_type = RadioWidget('schedule__schedule_type')

    @property
    def is_displayed(self):
        # Nothing is shown
        return False


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
        snapshot_tree = deferred_verpick({
            version.LOWEST: Tree("//div[@id='snapshots_treebox']/ul"),
            '5.7.0.1': BootstrapTreeview('snapshot_treebox')})

        def __init__(self, name=None, description=None, memory=None, parent_vm=None):
            super(Vm.Snapshot, self).__init__()
            self.name = name
            self.description = description
            self.memory = memory
            self.vm = parent_vm

        def _nav_to_snapshot_mgmt(self):
            snapshot_title = '"Snapshots" for Virtual Machine "{}"'.format(self.vm.name)
            if summary_title() != snapshot_title:
                self.vm.load_details()
                sel.click(InfoBlock.element("Properties", "Snapshots"))

        @property
        def exists(self):
            self._nav_to_snapshot_mgmt()
            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            try:
                self.snapshot_tree.find_path_to(
                    re.compile(r"{}.*?".format(title)))
                return True
            except CandidateNotFound:
                return False
            except NoSuchElementException:
                return False
            except NameError:
                return False

        def _click_tree_path(self, prop):
            """Find and click the given property in a snapshot tree path.

            Args:
                prop (str): Property to check (name or description).

            Returns:
                None
            """
            self.snapshot_tree.click_path(
                *self.snapshot_tree.find_path_to(re.compile(prop)))

        @property
        def active(self):
            """Check if the snapshot is active.

            Returns:
                bool: True if snapshot is active, False otherwise.
            """
            self._nav_to_snapshot_mgmt()
            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            try:
                self._click_tree_path(title)
                if sel.is_displayed_text("{} (Active)".format(title)):
                    return True
            except CandidateNotFound:
                return False
            return False

        def create(self, force_check_memory=False):
            snapshot_dict = {
                'description': self.description
            }
            self._nav_to_snapshot_mgmt()
            toolbar.select('Create a new snapshot for this VM')

            if self.name is not None:
                snapshot_dict['name'] = self.name

            if force_check_memory or self.vm.provider.mgmt.is_vm_running(self.vm.name):
                snapshot_dict["snapshot_memory"] = self.memory

            fill(snapshot_form, snapshot_dict, action=snapshot_form.create_button)
            wait_for(lambda: self.exists, num_sec=300, delay=20, fail_func=sel.refresh,
                     handle_exception=True)

        def delete(self, cancel=False):
            self._nav_to_snapshot_mgmt()

            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            self._click_tree_path(title)

            toolbar.select('Delete Snapshots', 'Delete Selected Snapshot', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            if not cancel:
                flash_message = version.pick({
                    version.LOWEST: "Remove Snapshot initiated for 1 "
                                    "VM and Instance from the CFME Database",
                    version.UPSTREAM: "Delete Snapshot initiated for 1 "
                                      "VM and Instance from the ManageIQ Database",
                    '5.9': "Delete Snapshot initiated for 1 VM and Instance from the CFME Database"
                })

                flash.assert_message_match(flash_message)

            wait_for(lambda: not self.exists, num_sec=300, delay=20, fail_func=sel.refresh)

        def delete_all(self, cancel=False):
            self._nav_to_snapshot_mgmt()
            toolbar.select('Delete Snapshots', 'Delete All Existing Snapshots', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            if not cancel:
                flash_message = version.pick({
                    version.LOWEST: "Remove All Snapshots initiated for 1 VM and "
                                    "Instance from the CFME Database",
                    version.UPSTREAM: "Delete All Snapshots initiated for 1 VM "
                                      "and Instance from the ManageIQ Database",
                    '5.9': "Delete All Snapshots initiated for 1 VM "
                           "and Instance from the CFME Database"})

                flash.assert_message_match(flash_message)

        def revert_to(self, cancel=False):
            self._nav_to_snapshot_mgmt()

            title = self.description if self.vm.provider.one_of(RHEVMProvider) else self.name
            self._click_tree_path(title)

            toolbar.select('Revert to selected snapshot', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            flash.assert_message_match('Revert To Snapshot initiated for 1 VM and Instance from '
                                       'the CFME Database')

        def refresh(self):
            self._nav_to_snapshot_mgmt()
            toolbar.select('Reload current display')

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
            'network': {'vlan': prov_data.get("vlan")},
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
        self.load_details(refresh=True)
        sel.click(InfoBlock("Properties", "Snapshots"))
        text = sel.text("//a[contains(normalize-space(.), '(Active)')]|"
            "//li[contains(normalize-space(.), '(Active)')]").strip()
        # In 5.6 the locator returns the entire tree string, snapshot name is after a newline
        return re.sub(r"\s*\(Active\)$", "", text.split('\n')[-1:][0])

    @property
    def current_snapshot_description(self):
        """Returns the current snapshot description."""
        self.load_details(refresh=True)
        sel.click(InfoBlock("Properties", "Snapshots"))
        l = "|".join([
            # Newer
            "//label[normalize-space(.)='Description']/../div/p",
            # Older
            "//td[@class='key' and normalize-space(.)='Description']/.."
            "/td[not(contains(@class, 'key'))]"])
        return sel.text(l).strip()

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
        relationship_form = Form(
            fields=[
                ('server_select', AngularSelect("server_id")),
                ('save_button', form_buttons.save),
                ('reset_button', form_buttons.reset),
                ('cancel_button', form_buttons.cancel)
            ])

        def __init__(self, o):
            self.o = o

        def navigate(self):
            self.o.load_details()
            cfg_btn('Edit Management Engine Relationship')

        def is_relationship_set(self):
            return "<Not a Server>" not in self.get_relationship()

        def get_relationship(self):
            self.navigate()
            rel = str(self.relationship_form.server_select.all_selected_options[0].text)
            form_buttons.cancel()
            return rel

        def set_relationship(self, server_name, server_id, click_cancel=False):
            self.navigate()
            option = "{} ({})".format(server_name, server_id)

            if click_cancel:
                fill(self.relationship_form, {'server_select': option},
                     action=self.relationship_form.cancel_button)
            else:
                fill(self.relationship_form, {'server_select': option})
                sel.click(form_buttons.FormButton(
                    "Save Changes", dimmed_alt="Save", force_click=True))
                flash.assert_success_message("Management Engine Relationship saved")

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

        vm_recfg = navigate_to(self, 'Reconfigure')

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
                row.mode.fill(mode)
                # Unit first, then size (otherwise JS would try to recalculate the size...)
                row[4].fill(disk.size_unit)
                row.size.fill(disk.size)
                row.dependent.fill(dependent)
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
    genealogy_tree = deferred_verpick({
        version.LOWEST: CheckboxTree("//div[@id='genealogy_treebox']/ul"),
        5.7: BootstrapTreeview('genealogy_treebox')
    })

    section_comparison_tree = CheckboxTree("//div[@id='all_sections_treebox']/div/table")
    apply_button = form_buttons.FormButton("Apply sections")

    mode_mapping = {
        "exists": "Exists Mode",
        "details": "Details Mode",
    }

    attr_mapping = {
        "all": "All Attributes",
        "different": "Attributes with different values",
        "same": "Attributes with same values",
    }

    def __init__(self, o):
        self.o = o

    def navigate(self):
        self.o.load_details()
        sel.click(InfoBlock.element("Relationships", "Genealogy"))

    def compare(self, *objects, **kwargs):
        """Compares two or more objects in the genealogy.

        Args:
            *objects: :py:class:`Vm` or :py:class:`Template` or :py:class:`str` with name.

        Keywords:
            sections: Which sections to compare.
            attributes: `all`, `different` or `same`. Default: `all`.
            mode: `exists` or `details`. Default: `exists`."""
        sections = kwargs.get("sections")
        attributes = kwargs.get("attributes", "all").lower()
        mode = kwargs.get("mode", "exists").lower()
        assert len(objects) >= 2, "You must specify at least two objects"
        objects = map(lambda o: o.name if isinstance(o, (Vm, Template)) else o, objects)
        self.navigate()
        for obj in objects:
            if not isinstance(obj, list):
                path = self.genealogy_tree.find_path_to(obj)
            self.genealogy_tree.check_node(*path)
        toolbar.select("Compare selected VMs")
        # COMPARE PAGE
        flash.assert_no_errors()
        if sections is not None:
            map(lambda path: self.section_comparison_tree.check_node(*path), sections)
            sel.click(self.apply_button)
            flash.assert_no_errors()
        # Set requested attributes sets
        toolbar.select(self.attr_mapping[attributes])
        # Set the requested mode
        toolbar.select(self.mode_mapping[mode])

    @property
    def tree(self):
        """Returns contents of the tree with genealogy"""
        self.navigate()
        return self.genealogy_tree.read_contents()

    @property
    def ancestors(self):
        """Returns list of ancestors of the represented object."""
        self.navigate()
        path = self.genealogy_tree.find_path_to(re.compile(r"^.*?\(Selected\)$"))
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
    if isinstance(vm_names, basestring):
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
        view.entities.get_entity(vm_name).check()


def find_quadicon(vm_name):
    """Find and return a quadicon belonging to a specific vm

    Args:
        vm: vm name as displayed at the quadicon
    Returns: entity of appropriate class
    """
    # todo: VMs have such method, so, this function is good candidate for removal
    view = navigate_to(Vm, 'VMsOnly')
    try:
        return view.entites.get_entity(vm_name, surf_pages=True)
    except ItemNotFound:
        raise VmNotFound("VM '{}' not found in UI!".format(vm_name))


def remove(vm_names, cancel=True, provider_crud=None):
    """Removes multiple VMs from CFME VMDB

    Args:
        vm_names: List of VMs to interact with
        cancel: Whether to cancel the deletion, defaults to True
        provider_crud: provider object where vm resides on (optional)
    """
    _method_setup(vm_names, provider_crud)
    cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


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
    entity = view.entites.get_entity(vm_name, surf_pages=True)
    return wait_for(_looking_for_state_change, func_args=[view, entity], num_sec=timeout)


def is_pwr_option_visible(vm_names, option, provider_crud=None):
    """Returns whether a particular power option is visible.

    Args:
        vm_names: List of VMs to interact with, if from_details=True is passed, only one VM can
            be passed in the list.
        option: Power option param.
        provider_crud: provider object where vm resides on (optional)
    """
    _method_setup(vm_names, provider_crud)
    try:
        toolbar.is_greyed('Power', option)
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
    _method_setup(vm_names, provider_crud)
    try:
        return not toolbar.is_greyed('Power', option)
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
    _method_setup(vm_names, provider_crud)

    if (is_pwr_option_visible(vm_names, provider_crud=provider_crud, option=option) and
            is_pwr_option_enabled(vm_names, provider_crud=provider_crud, option=option)):
                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel)


def perform_smartstate_analysis(vm_names, provider_crud=None, cancel=True):
    """Executes a refresh relationships action against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the refresh relationships action
    """
    _method_setup(vm_names, provider_crud)
    cfg_btn('Perform SmartState Analysis', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


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
    logger.info("Getting number of vms")
    if not do_not_navigate:
        navigate_to(Vm, 'VMsOnly')
    from cfme.web_ui import paginator
    if not paginator.page_controls_exist():
        logger.debug("No page controls")
        return 0
    total = paginator.rec_total()
    logger.debug("Number of VMs: %s", total)
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
                by_name=self.obj.name, surf_pages=True)
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
            row = self.prerequisite_view.entities.get_entity(by_name=self.obj.name,
                                                             surf_pages=True)
        except ItemNotFound:
            raise VmOrInstanceNotFound('Failed to locate VM/Template with name "{}"'.
                                       format(self.obj.name))
        row.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(Vm, 'Migrate')
class VmMigrate(CFMENavigateStep):
    VIEW = MigrateView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Migrate this VM")


@navigator.register(Vm, 'Clone')
class VmClone(CFMENavigateStep):
    VIEW = ProvisionView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select("Clone this VM")


@navigator.register(Vm, 'SetRetirement')
class SetRetirement(CFMENavigateStep):
    VIEW = RetirementView
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
