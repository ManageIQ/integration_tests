"""A model of Infrastructure Virtual Machines area of CFME.  This includes the VMs explorer tree,
quadicon lists, and VM details page.
"""
import re
from cfme.exceptions import CandidateNotFound, VmNotFound, OptionNotAvailable, TemplateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.services import requests
from cfme.web_ui import (
    CheckboxTree, Form, Region, Quadicon, Tree, accordion, fill, flash, form_buttons, paginator,
    toolbar, Calendar, Select
)
from cfme.web_ui.menu import nav
from functools import partial
from selenium.common.exceptions import NoSuchElementException
from utils.conf import cfme_data
from utils.log import logger
from utils.randomness import generate_random_string
from utils.timeutil import parsetime
from utils.virtual_machines import deploy_template
from utils.wait import wait_for, TimedOutError
from utils.mgmt_system import ActionNotSupported
from utils import version

QUADICON_TITLE_LOCATOR = ("//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_infra/x_show')"
                         " or contains(@href, '/show/')]")  # for provider specific vm/template page

details_page = Region(infoblock_type='detail')

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
        ('name', "//*[@id='name']"),
        ('descrition', "//*[@id='description']"),
        ('snapshot_memory', "//input[@id='snap_memory']"),
        ('create_button', create_button),
        ('cancel_button', form_buttons.cancel)
    ])


retire_form = Form(fields=[
    ('date_retire', Calendar("miq_date_1")),
    ('warn', sel.Select("select#retirement_warn"))
])


retirement_date_form = Form(fields=[
    ('retirement_date_text', Calendar("miq_date_1")),
    ('retirement_warning_select', Select("//select[@id='retirement_warn']"))
])

retire_remove_button = "//span[@id='remove_button']/a/img"

nav.add_branch(
    'infrastructure_virtual_machines',
    {
        "infra_vm_and_templates":
        [
            lambda _: accordion.tree("VMs & Templates", "All VMs & Templates"),
            {
                "vm_templates_provider_branch":
                [
                    lambda ctx: visible_tree.click_path(ctx["provider_name"]),
                    {
                        "datacenter_branch":
                        [
                            lambda ctx: visible_tree.click_path(ctx["datacenter_name"]),
                            {
                                "infra_vm_obj": lambda ctx: visible_tree.click_path(ctx["vm_name"]),
                            }
                        ],
                    }
                ],

                "vm_templates_archived_branch":
                [
                    lambda ctx: visible_tree.click_path("<Archived>"),
                    {
                        "infra_archive_obj":
                        lambda ctx: visible_tree.click_path(ctx["archive_name"]),
                    }
                ],

                "vm_templates_orphaned_branch":
                [
                    lambda ctx: visible_tree.click_path('<Orphaned>'),
                    {
                        "infra_orphan_obj": lambda ctx: visible_tree.click_path(ctx["orphan_name"]),
                    }
                ],
            }
        ],

        "infra_vms":
        [
            lambda _: accordion.tree("VMs", "All VMs"),
            {
                "infra_vms_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "infra_vms_filter": lambda ctx: visible_tree.click_path(ctx["filter_name"]),
                    }
                ],

                "infra_vm_by_name": lambda ctx: sel.click(ctx['vm'].find_quadicon(
                    do_not_navigate=True))
            }
        ],

        "infra_templates":
        [
            lambda _: (accordion.tree("Templates", "All Templates"), toolbar.set_vms_grid_view()),
            {
                "infra_templates_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "infra_templates_filter":
                        lambda ctx: visible_tree.click_path(ctx["filter_name"]),
                    }
                ],
            }
        ],
    }
)


class Common(object):

    def _load_details(self, refresh=False, is_vm=True):
        """Navigates to a VM's details page.

        Args:
            refresh: Refreshes the vm page if already there

        Raises:
            VmNotFound:
                When unable to find the VM passed
        """
        if not self.on_details(is_vm=is_vm):
            logger.debug("load_vm_details: not on details already")
            sel.click(self._find_quadicon(is_vm=is_vm))
        else:
            if refresh:
                toolbar.refresh()

    def on_details(self, force=False, is_vm=True):
        """A function to determine if the browser is already on the proper vm details page.
        """
        locator = ("//div[@class='dhtmlxInfoBarLabel' and contains(. , 'VM and Instance \"%s\"')]" %
                   self.name)
        if not sel.is_displayed(locator):
            if not force:
                return False
            else:
                self.load_details(is_vm=is_vm)
                return True

        text = sel.text(locator).encode("utf-8")
        pattern = r'("[A-Za-z0-9_\./\\-]*")'
        m = re.search(pattern, text)

        if not force:
            return self.name == m.group().replace('"', '')
        else:
            if self.name != m.group().replace('"', ''):
                self._load_details(is_vm=is_vm)
            else:
                return False

    def _find_quadicon(self, is_vm=True, do_not_navigate=False, mark=False, refresh=True):
        """Find and return a quadicon belonging to a specific vm

        Returns: :py:class:`cfme.web_ui.Quadicon` instance
        Raises: VmNotFound
        """
        quadicon = Quadicon(self.name, "vm")
        if not do_not_navigate:
            if is_vm:
                self.provider_crud.load_all_provider_vms()
            else:
                self.provider_crud.load_all_provider_templates()
            toolbar.set_vms_grid_view()
        elif refresh:
            sel.refresh()
        if not paginator.page_controls_exist():
            if is_vm:
                raise VmNotFound("VM '{}' not found in UI!".format(self.name))
            else:
                raise TemplateNotFound("Template '{}' not found in UI!".format(self.name))

        paginator.results_per_page(1000)
        for page in paginator.pages():
            if sel.is_displayed(quadicon):
                if mark:
                    sel.check(quadicon.checkbox())
                return quadicon
        else:
            raise VmNotFound("VM '{}' not found in UI!".format(self.name))

    def does_vm_exist_on_provider(self):
        """Check if VM exists on provider itself"""
        return self.provider_crud.get_mgmt_system().does_vm_exist(self.name)

    def _method_helper(self, from_details=False):
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(mark=True)

    def _remove_from_cfme(self, is_vm=True, cancel=True, from_details=False):
        """Removes a VM from CFME VMDB

        Args:
            cancel: Whether to cancel the deletion, defaults to True
            from_details: whether to delete from the details page
        """
        self._method_helper(from_details)
        if from_details:
            cfg_btn('Remove from the VMDB', invokes_alert=True)
        else:
            cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def delete_from_provider(self):
        provider_mgmt = self.provider_crud.get_mgmt_system()
        if provider_mgmt.does_vm_exist(self.name):
            try:
                if provider_mgmt.is_vm_suspended(self.name):
                    logger.debug("Powering up VM %s to shut it down correctly on %s." %
                                 (self.name, self.provider_crud.key))
                    provider_mgmt.start_vm(self.name)
            except ActionNotSupported:
                # Action is not supported on mgmt system. Simply continue
                pass
            return self.provider_crud.get_mgmt_system().delete_vm(self.name)
        else:
            return True

    def get_detail(self, properties=None, icon_href=False):
        """Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific vm.

        Args:
            properties: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"

        Returns:
            A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        if icon_href:
            return details_page.infoblock.icon_href(*properties)
        else:
            return details_page.infoblock.text(*properties)

    def get_tags(self):
        """Returns all tags that are associated with this VM"""
        self.load_details(refresh=True)
        # TODO: Make it count with different "My Company"
        table = details_page.infoblock.element("Smart Management", "My Company Tags")
        tags = []
        for row in sel.elements("./tbody/tr/td", root=table):
            tags.append(row.text.encode("utf-8").strip())
        return tags

    def refresh_relationships(self, from_details=False, cancel=False):
        """Executes a refresh relationships action against a list of VMs.

        Args:
            from_details: Whether or not to perform action from vm details page
            cancel: Whether or not to cancel the refresh relationships action
        """
        if from_details:
            self.load_details()
        else:
            self.find_quadicon(mark=True)
        cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def smartstate_scan(self, cancel=True, from_details=False):
        self._method_helper(from_details=from_details)
        cfg_btn('Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert(cancel=cancel)

    def wait_to_appear(self, is_vm=True, timeout=600, load_details=True):
        """Wait for a VM to appear within CFME

        Args:
            timeout: time (in seconds) to wait for it to appear
            from_details: when found, should it load the vm details
        """
        wait_for(self.does_vm_exist_in_cfme, num_sec=timeout, delay=30, fail_func=sel.refresh)
        if load_details:
            self.load_details()

    @property
    def genealogy(self):
        return Genealogy(self)


class Vm(Common):
    """Represents a VM in CFME

    Args:
        name: Name of the VM
        provider_crud: :py:class:`cfme.cloud.provider.Provider` object
        template_name: Name of the template to use for provisioning
    """

    class Snapshot(object):
        def __init__(self, name=None, description=None, memory=None, parent_vm=None):
            self.name = name
            self.description = description
            self.memory = memory
            self.vm = parent_vm

        def _nav_to_snapshot_mgmt(self):
            locator = ("//div[@class='dhtmlxInfoBarLabel' and " +
                       "contains(. , '\"Snapshots\" for Virtual Machine \"%s\"' % self.name) ]")
            if not sel.is_displayed(locator):
                self.vm.load_details()
                sel.click(details_page.infoblock.element("Properties", "Snapshots"))

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

    def __init__(self, name, provider_crud, template_name=None):
        self.name = name
        self.template_name = template_name
        self.provider_crud = provider_crud

    def create_on_provider(self, timeout=900, find_in_cfme=False):
        """Create the VM on the provider

        Args:
            timeout: Number of seconds to wait for the VM to appear in CFME
                     Will not wait at all, if set to 0 (Defaults to ``900``)
        """
        deploy_template(self.provider_crud.key, self.name, self.template_name)
        if find_in_cfme:
            self.provider_crud.refresh_provider_relationships()
            self.wait_to_appear(timeout=timeout, load_details=False, is_vm=True)

    def load_details(self, refresh=False):
        self._load_details(is_vm=True, refresh=refresh)

    def find_quadicon(self, do_not_navigate=False, mark=False, refresh=True):
        return self._find_quadicon(
            is_vm=True, do_not_navigate=do_not_navigate, mark=mark, refresh=refresh)

    def does_vm_exist_in_cfme(self):
        """A function to tell you if a VM exists or not.
        """
        try:
            self.find_quadicon()
            return True
        except VmNotFound:
            return False

    def remove_from_cfme(self, cancel=False, from_details=False):
        """Removes a VM from CFME VMDB"""
        self._remove_from_cfme(is_vm=True, cancel=cancel, from_details=from_details)

    def wait_for_delete(self):
        sel.force_navigate("infrastructure_virtual_machines")
        quad = Quadicon(self.name, 'vm')
        wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait template to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        sel.force_navigate("infrastructure_virtual_machines")
        quad = Quadicon(self.name, 'vm')
        wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait template to appear", num_sec=1000, fail_func=sel.refresh)
    # def _nav_to_cfme_relationship(self):
    #     pass

    # def edit_cfme_relationship(self, appliance_name):
    #     pass

    # def is_cfme_relationship_set(self):
    #     pass

    # def get_cfme_relationship_server(self):
    #     pass

    def power_control_from_provider(self, option):
        """Power control a vm from the provider

        Args:
            option: power control action to take against vm

        Raises:
            OptionNotAvailable: option parm must have proper value
        """
        if option == Vm.POWER_ON:
            self.provider_crud.get_mgmt_system().start_vm(self.name)
        elif option == Vm.POWER_OFF:
            self.provider_crud.get_mgmt_system().stop_vm(self.name)
        elif option == Vm.SUSPEND:
            self.provider_crud.get_mgmt_system().suspend_vm(self.name)
        # elif reset:
        # elif shutdown:
        else:
            raise OptionNotAvailable(option + " is not a supported action")

    def power_control_from_cfme(self, option, cancel=True, from_details=False):
        """Power controls a VM from within CFME

        Args:
            option: corresponds to option values under the power button
            cancel: Whether or not to cancel the power operation on confirmation
            from_details: Whether or not to perform action from vm details page
        """
        if (self.is_pwr_option_available_in_cfme(option=option, from_details=from_details)):
                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel)
                logger.info(
                    "Power control action of vm %s, option %s, cancel %s executed" %
                    (self.name, option, str(cancel)))
        else:
            raise OptionNotAvailable(option + " is not visible or enabled")

    def is_pwr_option_available_in_cfme(self, option, from_details=False):
        """Checks to see if a power option is available on the VM

        Args:
            option: corresponds to option values under the power button, preferred approach
                is to use Vm option constansts
            from_details: Whether or not to perform action from vm details page
        """
        self._method_helper(from_details=from_details)
        try:
            return not toolbar.is_greyed('Power', option)
        except NoSuchElementException:
            return False

    def retire(self):
        sel.force_navigate("infra_vm_by_name", context={'vm': self})
        lcl_btn("Retire this VM", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message(
            "Retire initiated for 1 VM and Instance from the CFME Database")

    @property
    def retirement_date(self):
        """Returns the retirement date of the selected machine.

        Returns:
            :py:class:`NoneType` if there is none, or :py:class:`utils.timeutil.parsetime`
        """
        date_str = self.get_detail(properties=("Lifecycle", "Retirement Date")).strip()
        if date_str.lower() == "never":
            return None
        return parsetime.from_american_date_only(date_str)

    def set_retirement_date(self, when, warn=None):
        """Sets the retirement date for this Vm object.

        It incorporates some magic to make it work reliably since the retirement form is not very
        pretty and it can't be just "done".

        Args:
            when: When to retire. :py:class:`str` in format mm/dd/yy of
                :py:class:`datetime.datetime` or :py:class:`utils.timeutil.parsetime`.
            warn: When to warn, fills the select in the form in case the ``when`` is specified.
        """
        self.load_details()
        lcl_btn("Set Retirement Date")
        sel.wait_for_element("#miq_date_1")
        if when is None:
            try:
                wait_for(lambda: sel.is_displayed(retire_remove_button), num_sec=5, delay=0.2)
                sel.click(retire_remove_button)
                wait_for(lambda: not sel.is_displayed(retire_remove_button), num_sec=10, delay=0.2)
                sel.click(form_buttons.save)
            except TimedOutError:
                pass
        else:
            if len(sel.value(retire_form.date_retire).strip()) > 0:
                sel.click(retire_remove_button)
                wait_for(lambda: not sel.is_displayed(retire_remove_button), num_sec=15, delay=0.2)
            fill(retire_form.date_retire, when)
            wait_for(lambda: sel.is_displayed(retire_remove_button), num_sec=15, delay=0.2)
            if warn is not None:
                fill(retire_form.warn, warn)
            sel.click(form_buttons.save)

    def publish_to_template(self, template_name, email=None, first_name=None, last_name=None):
        self.load_details()
        lcl_btn("Publish this VM to a Template")
        first_name = first_name or generate_random_string()
        last_name = last_name or generate_random_string()
        email = email or "{}@{}.test".format(first_name, last_name)
        try:
            prov_data = cfme_data["management_systems"][self.provider_crud.key]["provisioning"]
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
        return Template(template_name, self.provider_crud)

    def wait_for_vm_state_change(
            self, desired_state=None, timeout=300, from_details=False):
        """Wait for VM to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: on, off, suspended... corresponds to values in cfme, preferred approach
                is to use Vm.STATE_* constansts
            timeout: Specify amount of time (in seconds) to wait
        Raises:
            TimedOutError:
                When VM does not come up to desired state in specified period of time.
            NoVmFound:
                When unable to find the VM passed
        """
        def _looking_for_state_change():
            if from_details:
                self.load_details(refresh=True)
                detail_t = ("Power Management", "Power State")
                return self.get_detail(properties=detail_t) == desired_state
            else:
                return self.find_quadicon().state == 'currentstate-' + desired_state
        return wait_for(_looking_for_state_change, num_sec=timeout, delay=30)


class Template(Common):

    def __init__(self, name, provider_crud):
        self.name = name
        self.template_name = name
        self.provider_crud = provider_crud

    def load_details(self, refresh=False):
        self._load_details(refresh=refresh, is_vm=False)

    def find_quadicon(self, do_not_navigate=False, mark=False, refresh=True):
        return self._find_quadicon(
            is_vm=False, do_not_navigate=do_not_navigate, mark=mark, refresh=refresh)

    def remove_from_cfme(self, cancel=False, from_details=False):
        """Removes a VM from CFME VMDB"""
        self._remove_from_cfme(is_vm=False, cancel=cancel, from_details=from_details)

    def does_template_exist_in_cfme(self):
        """A function to tell you if a VM exists or not.
        """
        try:
            self.find_quadicon()
            return True
        except TemplateNotFound:
            return False

    def delete(self):
        """Remove template from CFME VMDB"""
        sel.force_navigate("infra_templates")
        quad = Quadicon(self.name, 'template')
        sel.check(quad.checkbox())
        cfg_btn('Remove Templates from the VMDB', invokes_alert=True)
        sel.handle_alert()

    def wait_for_delete(self):
        sel.force_navigate("infra_templates")
        quad = Quadicon(self.name, 'template')
        wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait template to disappear", num_sec=500, fail_func=sel.refresh)

    def wait_for_appear(self):
        sel.force_navigate("infra_templates")
        quad = Quadicon(self.name, 'template')
        wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait template to appear", num_sec=1000, fail_func=sel.refresh)


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
        sel.click(details_page.infoblock.element("Relationships", "Genealogy"))

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


def refresh_relationships(vm_names, provider_crud=None, cancel=True):
    """Executes a refresh relationships action against a list of VMs.

    Args:
        vm_names: List of VMs to interact with
        provider_crud: provider object where vm resides on (optional)
        cancel: Whether or not to cancel the refresh relationships action
    """
    _method_setup(vm_names, provider_crud)
    cfg_btn('Refresh Relationships and Power States', invokes_alert=True)
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


def get_first_vm_title(do_not_navigate=False):
    if not do_not_navigate:
        sel.force_navigate('infra_vms')
    return Quadicon.get_first_quad_title()


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


def _assign_unassign_policy_profiles(vm_name, assign, *policy_profile_names, **kwargs):
    """DRY function for managing policy profiles.

    See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

    Args:
        vm_name: Name of the VM.
        assign: Wheter to assign or unassign.
        policy_profile_names: :py:class:`str` with Policy Profile names.
    """
    if kwargs.get("via_details", True):
        sel.click(find_quadicon(vm_name))
    else:
        _method_setup(vm_name, **kwargs)
    toolbar.select("Policy", "Manage Policies")
    for policy_profile in policy_profile_names:
        if assign:
            manage_policies_tree.check_node(policy_profile)
        else:
            manage_policies_tree.uncheck_node(policy_profile)
    sel.click(form_buttons.save)


def assign_policy_profiles(vm_name, *policy_profile_names, **kwargs):
    """Assign Policy Profiles to specified VM.

    Args:
        vm_name: Name of the VM.
        policy_profile_names: :py:class:`str` with Policy Profile names.
    """
    return _assign_unassign_policy_profiles(vm_name, True, *policy_profile_names, **kwargs)


def unassign_policy_profiles(vm_name, *policy_profile_names, **kwargs):
    """Unassign Policy Profiles to specified VM.

    Args:
        vm_name: Name of the VM.
        policy_profile_names: :py:class:`str` with Policy Profile names.
    """
    return _assign_unassign_policy_profiles(vm_name, False, *policy_profile_names, **kwargs)


def load_archived_vms():
    """ Load list of archived vms """
    sel.force_navigate("vm_templates_archived_branch")
