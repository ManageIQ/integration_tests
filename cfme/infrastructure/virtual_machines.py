# -*- coding: utf-8 -*-
"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""
import fauxfactory
import re
from cfme.common.vm import VM as BaseVM, Template as BaseTemplate
from cfme.exceptions import CandidateNotFound, VmNotFound, OptionNotAvailable
from cfme.fixtures import pytest_selenium as sel
from cfme.services import requests
from cfme.web_ui import (
    CheckboxTree, Form, InfoBlock, Region, Quadicon, Tree, accordion, fill, flash, form_buttons,
    paginator, toolbar, Calendar, Select, Input, CheckboxTable, DriftGrid, summary_title
)
from cfme.web_ui.menu import extend_nav
from fixtures.pytest_store import store
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from utils.conf import cfme_data
from utils.log import logger
from utils.wait import wait_for
from utils import version
import cfme.web_ui.toolbar as tb


QUADICON_TITLE_LOCATOR = ("//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_infra/x_show')"
                         " or contains(@href, '/show/')]")  # for provider specific vm/template page

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


snapshot_tree = Tree("//div[@id='snapshots_treebox']/ul")

snapshot_form = Form(
    fields=[
        ('name', Input('name')),
        ('descrition', Input('description')),
        ('snapshot_memory', Input('snap_memory')),
        ('create_button', create_button),
        ('cancel_button', form_buttons.cancel)
    ])


retirement_date_form = Form(fields=[
    ('retirement_date_text', Calendar("miq_date_1")),
    ('retirement_warning_select', Select("//select[@id='retirement_warn']"))
])

retire_remove_button = "//span[@id='remove_button']/a/img"

vm_templates_tree = partial(accordion.tree, "VMs & Templates")
vms_tree = partial(accordion.tree, "VMs")
templates_tree = partial(accordion.tree, "Templates")

drift_table = CheckboxTable({
    version.LOWEST: "//table[@class='style3']",
    "5.4": "//th[normalize-space(.)='Timestamp']/ancestor::table[1]"
})


@extend_nav
class infrastructure_virtual_machines:
    def infra_vm_and_templates(_):
        vm_templates_tree("All VMs & Templates")

    def vm_templates_provider_branch(ctx):
        vm_templates_tree("All VMs & Templates", ctx["provider_name"])

    def datacenter_branch(ctx):
        vm_templates_tree("All VMs & Templates", ctx["provider_name"], ctx["datacenter_name"])

    def infra_vm_obj(ctx):
        vm_templates_tree(
            "All VMs & Templates", ctx["provider_name"], ctx["datacenter_name"], ctx["vm_name"])

    def vm_templates_archived_branch(ctx):
        vm_templates_tree("All VMs & Templates", "<Archived>")

    def infra_archive_obj(ctx):
        vm_templates_tree("All VMs & Templates", "<Archived>", ctx["archive_name"])

    def vm_templates_orphaned_branch(ctx):
        vm_templates_tree("All VMs & Templates", "<Orphaned>")

    def infra_orphan_obj(ctx):
        vm_templates_tree("All VMs & Templates", "<Orphaned>", ctx["orphan_name"])

    class infra_vms:
        def navigate(_):
            vms_tree("All VMs")

        def infra_vm_by_name(ctx):
            sel.click(ctx['vm'].find_quadicon(do_not_navigate=True))

    def infra_vms_filter_folder(ctx):
        vms_tree("All VMs", ctx["folder_name"])

    def infra_vms_filter(ctx):
        vms_tree("All VMs", ctx["folder_name"], ctx["filter_name"])

    def infra_templates(_):
        templates_tree("All Templates")
        toolbar.select('Grid View')

    def infra_templates_filter_folder(ctx):
        templates_tree("All Templates", ctx["folder_name"])

    def infra_templates_filter(ctx):
        templates_tree("All Templates", ctx["folder_name"], ctx["filter_name"])


class Common(object):
    """Stuff shared for bot hVM and Template."""
    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper vm details page.
        """
        title = '{} "{}"'.format(
            "VM and Instance" if self.is_vm else "VM Template and Image", self.name)
        present_title = summary_title()
        if present_title is None or title not in present_title:
            if not force:
                return False
            else:
                self.load_details()
                return True

        pattern = r'("[A-Za-z0-9_\./\\-]*")'
        m = re.search(pattern, present_title)

        if not force:
            return self.name == m.group().replace('"', '')
        else:
            if self.name != m.group().replace('"', ''):
                self._load_details()
            else:
                return False

    @property
    def genealogy(self):
        return Genealogy(self)


@BaseVM.register_for_provider_type("infra")
class Vm(BaseVM, Common):
    """Represents a VM in CFME

    Args:
        name: Name of the VM
        provider_crud: :py:class:`cfme.cloud.provider.Provider` object
        template_name: Name of the template to use for provisioning
    """

    class Snapshot(object):
        def __init__(self, name=None, description=None, memory=None, parent_vm=None):
            super(Vm.Snapshot, self).__init__()
            self.name = name
            self.description = description
            self.memory = memory
            self.vm = parent_vm

        def _nav_to_snapshot_mgmt(self):
            locator = ("//div[@class='dhtmlxInfoBarLabel' and contains(. , " +
                       "'\"Snapshots\" for Virtual Machine \"{}\"') ]".format(self.name))
            if not sel.is_displayed(locator):
                self.vm.load_details()
                sel.click(InfoBlock.element("Properties", "Snapshots"))

        def does_snapshot_exist(self):
            self._nav_to_snapshot_mgmt()
            try:
                snapshot_tree.find_path_to(re.compile(r".*?\(Active\)$"))
                return True
            except CandidateNotFound:
                try:
                    snapshot_tree.find_path_to(re.compile(self.name))
                    return True
                except CandidateNotFound:
                    return False
            except NoSuchElementException:
                return False

        def wait_for_snapshot_active(self):
            self._nav_to_snapshot_mgmt()
            try:
                snapshot_tree.click_path(*snapshot_tree.find_path_to(re.compile(self.name)))
                if sel.is_displayed_text(self.name + " (Active)"):
                    return True
            except CandidateNotFound:
                return False

        def create(self):
            self._nav_to_snapshot_mgmt()
            toolbar.select('Create a new snapshot for this VM')
            fill(snapshot_form, {'name': self.name,
                                 'description': self.description,
                                 'snapshot_memory': self.memory
                                 },
                 action=snapshot_form.create_button)
            wait_for(self.does_snapshot_exist, num_sec=300, delay=20, fail_func=sel.refresh)

        def delete(self, cancel=False):
            self._nav_to_snapshot_mgmt()
            toolbar.select('Delete Snapshots', 'Delete Selected Snapshot', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            if not cancel:
                if version.current_version() >= "5.5":
                    flash.assert_message_match(
                        'Remove Snapshot initiated for 1 VM and Instance from the CFME Database')
                else:
                    flash.assert_message_match(
                        'Delete Snapshot initiated for 1 VM and Instance from the CFME Database')

        def delete_all(self, cancel=False):
            self._nav_to_snapshot_mgmt()
            toolbar.select('Delete Snapshots', 'Delete All Existing Snapshots', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            if not cancel:
                if version.current_version() >= "5.5":
                    flash.assert_message_match(
                        'Remove All Snapshots initiated for 1 VM and Instance from the '
                        'CFME Database')
                else:
                    flash.assert_message_match(
                        'Delete All Snapshots initiated for 1 VM and Instance from the CFME '
                        'Database')

        def revert_to(self, cancel=False):
            self._nav_to_snapshot_mgmt()
            snapshot_tree.click_path(*snapshot_tree.find_path_to(re.compile(self.name)))
            toolbar.select('Revert to selected snapshot', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            if version.current_version() >= "5.5":
                flash.assert_message_match(
                    'Revert To Snapshot initiated for 1 VM and Instance from the CFME Database')
            else:
                flash.assert_message_match(
                    'Revert To A Snapshot initiated for 1 VM and Instance from the CFME Database')

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
        sel.force_navigate("infra_vm_by_name", context={'vm': self})
        lcl_btn("Migrate this VM")
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")
        provisioning_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "host_name": {"name": prov_data.get("host")},
            "datastore_name": {"name": prov_data.get("datastore")}
        }
        from cfme.provisioning import provisioning_form
        fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)

    def clone_vm(self, email=None, first_name=None, last_name=None,
                 vm_name=None, provision_type=None):
        sel.force_navigate("infra_vm_by_name", context={'vm': self})
        lcl_btn("Clone this VM")
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")
        provisioning_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "provision_type": provision_type,
            "vm_name": vm_name,
            "host_name": {"name": prov_data.get("host")},
            "datastore_name": {"name": prov_data.get("datastore")},
            "vlan": prov_data.get("vlan")
        }
        from cfme.provisioning import provisioning_form
        fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)

    def publish_to_template(self, template_name, email=None, first_name=None, last_name=None):
        self.load_details()
        lcl_btn("Publish this VM to a Template")
        first_name = first_name or fauxfactory.gen_alphanumeric()
        last_name = last_name or fauxfactory.gen_alphanumeric()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider.key]["provisioning"]
        except (KeyError, IndexError):
            raise ValueError("You have to specify the correct options in cfme_data.yaml")

        provisioning_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "vm_name": template_name,
            "host_name": {"name": prov_data.get("host")},
            "datastore_name": {"name": prov_data.get("datastore")},
        }
        from cfme.provisioning import provisioning_form
        fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)
        cells = {'Description': 'Publish from [{}] to [{}]'.format(self.name, template_name)}
        row, __ = wait_for(
            requests.wait_for_request, [cells], fail_func=requests.reload, num_sec=900, delay=20)
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
        text = sel.text("//a[contains(normalize-space(.), '(Active)')]").strip()
        return re.sub(r"\s*\(Active\)$", "", text)

    @property
    def current_snapshot_description(self):
        """Returns the current snapshot name."""
        self.load_details(refresh=True)
        sel.click(InfoBlock("Properties", "Snapshots"))
        l = "|".join([
            # Newer
            "//label[normalize-space(.)='Description']/../div/p",
            # Older
            "//td[@class='key' and normalize-space(.)='Description']/.."
            "/td[not(contains(@class, 'key'))]"])
        return sel.text(l).strip()

    def get_vm_via_rest(self):
        return store.current_appliance.rest_api.collections.vms.get(name=self.name)

    def get_collection_via_rest(self):
        return store.current_appliance.rest_api.collections.vms

    def equal_drift_results(self, row_text, section, *indexes):
        """ Compares drift analysis results of a row specified by it's title text

        Args:
            row_text: Title text of the row to compare
            section: Accordion section where the change happened; this section must be activated
            indexes: Indexes of results to compare starting with 0 for first row (latest result).
                     Compares all available drifts, if left empty (default).

        Note:
            There have to be at least 2 drift results available for this to work.

        Returns:
            ``True`` if equal, ``False`` otherwise.
        """
        # mark by indexes or mark all
        self.load_details(refresh=True)
        sel.click(InfoBlock("Properties", "Drift History"))
        if indexes:
            drift_table.select_rows_by_indexes(*indexes)
        else:
            # We can't compare more than 10 drift results at once
            # so when selecting all, we have to limit it to the latest 10
            if len(list(drift_table.rows())) > 10:
                drift_table.select_rows_by_indexes(*range(0, min(10, len)))
            else:
                drift_table.select_all()
        tb.select("Select up to 10 timestamps for Drift Analysis")

        # Make sure the section we need is active/open
        sec_loc_map = {
            'Properties': 'Properties',
            'Security': 'Security',
            'Configuration': 'Configuration',
            'My Company Tags': 'Categories'}
        sec_loc_template = "//div[@id='all_sections_treebox']//li[contains(@id, 'group_{}')]"\
            "//span[contains(@class, 'dynatree-checkbox')]"
        sec_checkbox_loc = "//div[@id='all_sections_treebox']//li[contains(@id, 'group_{}')]"\
            "//span[contains(@class, 'dynatree-checkbox')]".format(sec_loc_map[section])
        sec_apply_btn = "//div[@id='accordion']/a[contains(normalize-space(text()), 'Apply')]"

        # Deselect other sections
        for other_section in sec_loc_map.keys():
            other_section_loc = sec_loc_template.format(sec_loc_map[other_section])
            other_section_classes = sel.get_attribute(other_section_loc + '/..', "class")
            if other_section != section and 'dynatree-partsel' in other_section_classes:
                # Element needs to be checked out if it has no dynatree-selected
                if 'dynatree-selected' not in other_section_classes:
                    sel.click(other_section_loc)
                sel.click(other_section_loc)

        # Activate the required section
        sel.click(sec_checkbox_loc)
        sel.click(sec_apply_btn)

        if not tb.is_active("All attributes"):
            tb.select("All attributes")
        d_grid = DriftGrid()
        if any(d_grid.cell_indicates_change(row_text, i) for i in range(0, len(indexes))):
            return False
        return True

    class CfmeRelationship(object):

        relationship_form = Form(
            fields=[
                ('server_select', Select("//*[@id='server_id']")),
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
                fill(self.relationship_form, {'server_select': option},
                     action=self.relationship_form.save_button)
                # something weird going on where changing the select doesn't POST to undim save
                sel.wait_for_ajax()
                if self.relationship_form.save_button.is_dimmed:
                    logger.warning("Worked around dimmed save button")
                    sel.browser().execute_script(
                        "$j.ajax({type: 'POST', url: '/vm_infra/evm_relationship_field_changed',"
                        " data: {'server_id':'%s'}})" % (server_id))
                    sel.click(form_buttons.FormButton(
                        "Save Changes", dimmed_alt="Save", force_click=True))
                flash.assert_success_message("Management Engine Relationship saved")


@BaseTemplate.register_for_provider_type("infra")
class Template(BaseTemplate, Common):
    REMOVE_MULTI = "Remove Templates from the VMDB"


class Genealogy(object):
    """Class, representing genealogy of an infra object with possibility of data retrieval
    and comparison.

    Args:
        o: The :py:class:`Vm` or :py:class:`Template` object.
    """
    genealogy_tree = CheckboxTree("//div[@id='genealogy_treebox']/ul")

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
        sections = kwargs.get("sections", None)
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
def _method_setup(vm_names, provider_crud=None):
    """ Reduces some redundant code shared between methods """
    if isinstance(vm_names, basestring):
        vm_names = [vm_names]

    if provider_crud:
        provider_crud.load_all_provider_vms()
    else:
        sel.force_navigate('infra_vms')
    if paginator.page_controls_exist():
        paginator.results_per_page(1000)
    for vm_name in vm_names:
        sel.check(Quadicon(vm_name, 'vm').checkbox())


def find_quadicon(vm_name, do_not_navigate=False):
    """Find and return a quadicon belonging to a specific vm

    Args:
        vm: vm name as displayed at the quadicon
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    if not paginator.page_controls_exist():
        raise VmNotFound("VM '{}' not found in UI!".format(vm_name))

    paginator.results_per_page(1000)
    for page in paginator.pages():
        quadicon = Quadicon(vm_name, "vm")
        if sel.is_displayed(quadicon):
            return quadicon
    else:
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
    def _looking_for_state_change():
        toolbar.refresh()
        return 'currentstate-' + desired_state in find_quadicon(
            vm_name, do_not_navigate=False).state

    _method_setup(vm_name, provider_crud)
    return wait_for(_looking_for_state_change, num_sec=timeout)


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
    """Returns list of all vms"""
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    vms = set([])

    # This is really stupid, but I cannot come up with better getting of the attributes :(
    if not paginator.page_controls_exist():
        for title in sel.elements(QUADICON_TITLE_LOCATOR):
            title_value = sel.get_attribute(title, "title")
            if not title_value:
                title_value = sel.get_attribute(title, "data-original-title")
            vms.add(title_value)
        return vms

    paginator.results_per_page(1000)
    for page in paginator.pages():
        try:
            for page in paginator.pages():
                for title in sel.elements(QUADICON_TITLE_LOCATOR):
                    title_value = sel.get_attribute(title, "title")
                    if not title_value:
                        title_value = sel.get_attribute(title, "data-original-title")
                    vms.add(title_value)
        except sel.NoSuchElementException:
            pass
    return vms


def get_number_of_vms(do_not_navigate=False):
    """
    Returns the total number of VMs visible to the user,
    including those archived or orphaned
    """
    logger.info("Getting number of vms")
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    if not paginator.page_controls_exist():
        logger.debug("No page controls")
        return 0
    total = paginator.rec_total()
    logger.debug("Number of VMs: %s", total)
    return int(total)
