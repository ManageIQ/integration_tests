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
    paginator, toolbar, Calendar, Select, Input
)
from cfme.web_ui.menu import extend_nav
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from utils.conf import cfme_data
from utils.log import logger
from utils.wait import wait_for
from utils import version


QUADICON_TITLE_LOCATOR = ("//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_infra/x_show')"
                         " or contains(@href, '/show/')]")  # for provider specific vm/template page

cfg_btn = partial(toolbar.select, 'Configuration')
pol_btn = partial(toolbar.select, 'Policy')
lcl_btn = partial(toolbar.select, 'Lifecycle')
mon_btn = partial(toolbar.select, 'Monitoring')
pwr_btn = partial(toolbar.select, 'Power')

create_button = form_buttons.FormButton("Create")

visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div"
                    "/ul[@class='dynatree-container']")

manage_policies_tree = CheckboxTree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    }
)


manage_policies_page = Region(
    locators={
        'save_button': form_buttons.save,
    })


snapshot_tree = Tree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='snapshots_treebox']/ul"
    }
)

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


@extend_nav
class infrastructure_virtual_machines(object):
    class infra_vm_and_templates(object):
        def navigate(_):
            accordion.tree("VMs & Templates", "All VMs & Templates")

        class vm_templates_provider_branch(object):
            def navigate(ctx):
                visible_tree.click_path(ctx["provider_name"])

            class datacenter_branch(object):
                def navigate(ctx):
                    visible_tree.click_path(ctx["datacenter_name"])

                def infra_vm_obj(ctx):
                    visible_tree.click_path(ctx["vm_name"])

        class vm_templates_archived_branch(object):
            def navigate(ctx):
                visible_tree.click_path("<Archived>")

            def infra_archive_obj(ctx):
                visible_tree.click_path(ctx["archive_name"])

        class vm_templates_orphaned_branch(object):
            def navigate(ctx):
                visible_tree.click_path("<Orphaned>")

            def infra_orphan_obj(ctx):
                visible_tree.click_path(ctx["orphan_name"])

    class infra_vms(object):
        def navigate(_):
            accordion.tree("VMs", "All VMs")

        class infra_vms_filter_folder(object):
            def navigate(ctx):
                visible_tree.click_path(ctx["folder_name"])

            def infra_vms_filter(ctx):
                visible_tree.click_path(ctx["filter_name"])

        def infra_vm_by_name(ctx):
            sel.click(ctx['vm'].find_quadicon(do_not_navigate=True))

    class infra_templates(object):
        def navigate(_):
            accordion.tree("Templates", "All Templates")
            toolbar.set_vms_grid_view()

        class infra_templates_filter_folder(object):
            def navigate(ctx):
                visible_tree.click_path(ctx["folder_name"])

            def infra_templates_filter(ctx):
                visible_tree.click_path(ctx["filter_name"])


class Common(object):
    """Stuff shared for bot hVM and Template."""
    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper vm details page.
        """
        locator = "//div[@class='dhtmlxInfoBarLabel' and contains(. , '{} \"{}\"')]".format(
            "VM and Instance" if self.is_vm else "VM Template and Image", self.name)
        if not sel.is_displayed(locator):
            if not force:
                return False
            else:
                self.load_details()
                return True

        text = sel.text(locator).encode("utf-8")
        pattern = r'("[A-Za-z0-9_\./\\-]*")'
        m = re.search(pattern, text)

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
            locator = ("//div[@class='dhtmlxInfoBarLabel' and " +
                       "contains(. , '\"Snapshots\" for Virtual Machine \"%s\"') ]" % self.name)
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
                flash.assert_message_match(
                    'Delete Snapshot initiated for 1 VM and Instance from the CFME Database')

        def delete_all(self, cancel=False):
            self._nav_to_snapshot_mgmt()
            toolbar.select('Delete Snapshots', 'Delete All Existing Snapshots', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
            if not cancel:
                flash.assert_message_match(
                    'Delete All Snapshots initiated for 1 VM and Instance from the CFME Database')

        def revert_to(self, cancel=False):
            self._nav_to_snapshot_mgmt()
            snapshot_tree.click_path(*snapshot_tree.find_path_to(re.compile(self.name)))
            toolbar.select('Revert to selected snapshot', invokes_alert=True)
            sel.handle_alert(cancel=cancel)
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
            prov_data = cfme_data["management_systems"][self.provider_crud.key]["provisioning"]
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
        cells = {'Description': 'Publish from [%s] to [%s]' % (self.name, template_name)}
        row, __ = wait_for(
            requests.wait_for_request, [cells], fail_func=requests.reload, num_sec=900, delay=20)
        return Template(template_name, self.provider)

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
            option = "%s (%d)" % (server_name, server_id)

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
    genealogy_tree = CheckboxTree({
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='genealogy_treebox']/ul",
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
        find_quadicon(vm_name, do_not_navigate=False).state == 'currentstate-' + desired_state

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
    if not paginator.page_controls_exist():
        return vms

    paginator.results_per_page(1000)
    for page in paginator.pages():
        try:
            for page in paginator.pages():
                for title in sel.elements(QUADICON_TITLE_LOCATOR):
                    vms.add(sel.get_attribute(title, "title"))
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
    logger.debug("Number of VMs: {}".format(total))
    return int(total)
