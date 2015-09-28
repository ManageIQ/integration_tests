""" A model of Instances page in CFME

:var edit_form: A :py:class:`cfme.web_ui.Form` object describing the instance edit form.
"""
from cfme.common.vm import VM, Template
from cfme.exceptions import InstanceNotFound, OptionNotAvailable
from cfme.fixtures import pytest_selenium as sel
from cfme.services import requests
from cfme.web_ui import (
    accordion, fill, flash, paginator, toolbar, CheckboxTree, Form, Region, Select, Tree, Quadicon)
from cfme.web_ui.menu import nav
from functools import partial
from utils import deferred_verpick, version
from utils.wait import wait_for


cfg_btn = partial(toolbar.select, 'Configuration')
pwr_btn = partial(toolbar.select, 'Power')

# TODO: use accordion.tree
visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div"
                    "/ul[@class='dynatree-container']")

list_page = Region(title='Instances')

policy_page = Region(
    locators={
        'policy_tree': Tree('//div[@class="containerTableStyle"]/table')
    })

manage_policies_tree = CheckboxTree(
    {
        version.LOWEST: "//div[@id='treebox']/div/table",
        "5.3": "//div[@id='protect_treebox']/ul"
    }
)

# Forms
edit_form = Form(
    fields=[
        ('custom_ident', "//*[@id='custom_1']"),
        ('description_tarea', "//textarea[@id='description']"),
        ('parent_sel', Select("//select[@name='chosen_parent']")),
        ('child_sel', Select("//select[@id='kids_chosen']", multi=True)),
        ('vm_sel', Select("//select[@id='choices_chosen']", multi=True)),
        ('add_btn', "//img[@alt='Move selected VMs to left']"),
        ('remove_btn', "//img[@alt='Move selected VMs to right']"),
        ('remove_all_btn', "//img[@alt='Move all VMs to right']"),
    ])


nav.add_branch(
    "clouds_instances",
    {
        "clouds_instances_by_provider":
        [
            lambda _: accordion.tree("Instances by Provider", "Instances by Provider"),
            {
                "clouds_instances_provider_branch":
                [
                    lambda ctx: visible_tree.click_path(ctx["provider_name"]),
                    {
                        "availability_zone_branch":
                        [
                            lambda ctx: visible_tree.click_path(ctx["availability_zone"]),
                            {
                                "clouds_instance_obj":
                                lambda ctx: visible_tree.click_path(ctx["instance_name"])
                            }
                        ]
                    }
                ],

                "clouds_instances_archived_branch":
                [
                    lambda ctx: visible_tree.click_path('<Archived>'),
                    {
                        "clouds_instance_archive_obj":
                        lambda ctx: visible_tree.click_path(ctx["archive_name"]),
                    }
                ],

                "clouds_instances_orphaned_branch":
                [
                    lambda ctx: visible_tree.click_path('<Orphaned>'),
                    {
                        "clouds_instance_orphan_obj":
                        lambda ctx: visible_tree.click_path(ctx["orphan_name"]),
                    }
                ],
            }
        ],

        "clouds_images_by_provider":
        [
            lambda _: accordion.tree("Images by Provider", "Images by Provider"),
            {
                "clouds_images_provider_branch":
                [
                    lambda ctx: visible_tree.click_path(ctx["provider_name"]),
                    {
                        "availability_zone_branch":
                        [
                            lambda ctx: visible_tree.click_path(ctx["availability_zone"]),
                            {
                                "clouds_image_obj":
                                lambda ctx: visible_tree.click_path(ctx["image_name"])
                            }
                        ]
                    }
                ],

                "clouds_images_archived_branch":
                [
                    lambda ctx: visible_tree.click_path('<Archived>'),
                    {
                        "clouds_image_archive_obj":
                        lambda ctx: visible_tree.click_path(ctx["archive_name"]),
                    }
                ],

                "clouds_images_orphaned_branch":
                [
                    lambda ctx: visible_tree.click_path('<Orphaned>'),
                    {
                        "clouds_image_orphan_obj":
                        lambda ctx: visible_tree.click_path(ctx["orphan_name"]),
                    }
                ],
            }
        ],

        "clouds_instances":
        [
            lambda _: accordion.tree("Instances", "All Instances"),
            {
                "clouds_instances_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "clouds_instances_filter":
                        lambda ctx: visible_tree.click_path(ctx["filter_name"])
                    }
                ]
            }
        ],

        "clouds_images":
        [
            lambda _: (accordion.tree("Images", "All Images")),
            {
                "clouds_images_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "clouds_images_filter":
                        lambda ctx: visible_tree.click_path(ctx["filter_name"])
                    }
                ]
            }
        ]
    }
)


@VM.register_for_provider_type("cloud")
class Instance(VM):
    """Represents a generic instance in CFME. This class is used if none of the inherited classes
    will match.

    Args:
        name: Name of the instance
        provider_crud: :py:class:`cfme.cloud.provider.Provider` object
        template_name: Name of the template to use for provisioning

    Note:
        This class cannot be instantiated. Use :py:func:`instance_factory` instead.
    """
    ALL_LIST_LOCATION = "clouds_instances"
    TO_OPEN_EDIT = "Edit this Instance"
    TO_RETIRE = "Retire this Instance"
    QUADICON_TYPE = "instance"

    def create(self):
        """Provisions an instance with the given properties through CFME
        """
        raise NotImplementedError('create is not implemented.')

    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper instance details page.
        """
        locator = ("//div[@class='dhtmlxInfoBarLabel' and contains(. , 'Instance \"%s\"')]" %
            self.name)

        # If the locator isn't on the page, or if it _is_ on the page and contains
        # 'Timelines' we are on the wrong page and take the appropriate action
        if not sel.is_displayed(locator):
            wrong_page = True
        else:
            wrong_page = 'Timelines' in sel.text(locator)

        if wrong_page:
            if not force:
                return False
            else:
                self.load_details()
                return True

        text = sel.text(locator).encode("utf-8")
        pattern = r'("[A-Za-z0-9_\./\\-]*")'
        import re
        m = re.search(pattern, text)

        if not force:
            return self.name == m.group().replace('"', '')
        else:
            if self.name != m.group().replace('"', ''):
                self.load_details()
                return True
            else:
                return True


@VM.register_for_provider_type("openstack")
class OpenStackInstance(Instance):
    # CFME & provider power control options
    START = "Start"  # START also covers RESUME and UNPAUSE (same as in CFME 5.4+ web UI)
    POWER_ON = START  # For compatibility with the infra objects.
    SUSPEND = "Suspend"
    TERMINATE = "Terminate"
    # CFME-only power control options
    SOFT_REBOOT = "Soft Reboot"
    HARD_REBOOT = "Hard Reboot"
    # Provider-only power control options
    STOP = "Stop"
    PAUSE = "Pause"
    RESTART = "Restart"

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_ERROR = "non-operational"
    STATE_PAUSED = deferred_verpick({
        version.LOWEST: "off",
        "5.4": "paused",
    })
    STATE_SUSPENDED = deferred_verpick({
        version.LOWEST: "off",
        "5.4": "suspended",
    })
    STATE_UNKNOWN = "unknown"

    def create(self, email=None, first_name=None, last_name=None, cloud_network=None,
               instance_type=None, cancel=False, **prov_fill_kwargs):
        """Provisions an OpenStack instance with the given properties through CFME

        Args:
            email: Email of the requester
            first_name: Name of the requester
            last_name: Surname of the requester
            cloud_network: Name of the cloud network the instance should belong to
            instance_type: Type of the instance
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.provisioning_form`
        """
        from cfme.provisioning import provisioning_form
        sel.force_navigate('clouds_provision_instances', context={
            'provider': self.provider,
            'template_name': self.template_name,
        })

        # not supporting multiselect now, just take first value
        security_groups = prov_fill_kwargs.pop('security_groups', None)
        if security_groups:
            prov_fill_kwargs['security_groups'] = security_groups[0]

        fill(provisioning_form, dict(
            email=email,
            first_name=first_name,
            last_name=last_name,
            instance_name=self.name,
            instance_type=instance_type,
            cloud_network=cloud_network,
            **prov_fill_kwargs
        ))

        if cancel:
            sel.click(provisioning_form.cancel_button)
            flash.assert_success_message(
                "Add of new VM Provision Request was cancelled by the user")
        else:
            sel.click(provisioning_form.submit_button)
            flash.assert_success_message(
                "VM Provision Request was Submitted, you will be notified when your VMs are ready")

        row_description = 'Provision from [%s] to [%s]' % (self.template_name, self.name)
        cells = {'Description': row_description}
        row, __ = wait_for(requests.wait_for_request, [cells],
                           fail_func=requests.reload, num_sec=600, delay=20)
        assert row.last_message.text == version.pick(
            {version.LOWEST: 'VM Provisioned Successfully',
             "5.3": 'Vm Provisioned Successfully', })

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance

        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == OpenStackInstance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == OpenStackInstance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == OpenStackInstance.SUSPEND:
            self.provider.mgmt.suspend_vm(self.name)
        elif option == OpenStackInstance.RESUME:
            self.provider.mgmt.resume_vm(self.name)
        elif option == OpenStackInstance.PAUSE:
            self.provider.mgmt.pause_vm(self.name)
        elif option == OpenStackInstance.UNPAUSE:
            self.provider.mgmt.unpause_vm(self.name)
        elif option == OpenStackInstance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == OpenStackInstance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")


@VM.register_for_provider_type("ec2")
class EC2Instance(Instance):
    # CFME & provider power control options
    START = "Start"
    POWER_ON = START  # For compatibility with the infra objects.
    STOP = "Stop"
    TERMINATE = "Terminate"
    # CFME-only power control options
    SOFT_REBOOT = "Soft Reboot"
    # Provider-only power control options
    RESTART = "Restart"

    # CFME power states
    STATE_ON = "on"
    STATE_OFF = "off"
    STATE_SUSPENDED = "suspended"
    STATE_UNKNOWN = "unknown"

    def create(self, email=None, first_name=None, last_name=None, availability_zone=None,
               security_groups=None, instance_type=None, guest_keypair=None, cancel=False,
               **prov_fill_kwargs):
        """Provisions an EC2 instance with the given properties through CFME

        Args:
            email: Email of the requester
            first_name: Name of the requester
            last_name: Surname of the requester
            availability_zone: Name of the zone the instance should belong to
            security_groups: List of security groups the instance should belong to
                             (currently, only the first one will be used)
            instance_type: Type of the instance
            guest_keypair: Name of the key pair used to access the instance
            cancel: Clicks the cancel button if `True`, otherwise clicks the submit button
                    (Defaults to `False`)
        Note:
            For more optional keyword arguments, see
            :py:data:`cfme.cloud.provisioning.provisioning_form`
        """
        from cfme.provisioning import provisioning_form
        sel.force_navigate('clouds_provision_instances', context={
            'provider': self.provider,
            'template_name': self.template_name,
        })

        fill(provisioning_form, dict(
            email=email,
            first_name=first_name,
            last_name=last_name,
            instance_name=self.name,
            availability_zone=availability_zone,
            # not supporting multiselect now, just take first value
            security_groups=security_groups[0],
            instance_type=instance_type,
            guest_keypair=guest_keypair,
            **prov_fill_kwargs
        ))

        if cancel:
            sel.click(provisioning_form.cancel_button)
            flash.assert_success_message(
                "Add of new VM Provision Request was cancelled by the user")
        else:
            sel.click(provisioning_form.submit_button)
            flash.assert_success_message(
                "VM Provision Request was Submitted, you will be notified when your VMs are ready")

        row_description = 'Provision from [%s] to [%s]' % (self.template_name, self.name)
        cells = {'Description': row_description}
        row, __ = wait_for(requests.wait_for_request, [cells],
                           fail_func=requests.reload, num_sec=900, delay=20)
        assert row.last_message.text == version.pick(
            {version.LOWEST: 'VM Provisioned Successfully',
             "5.3": 'Vm Provisioned Successfully', })

    def power_control_from_provider(self, option):
        """Power control the instance from the provider

        Args:
            option: power control action to take against instance

        Raises:
            OptionNotAvailable: option param must have proper value
        """
        if option == EC2Instance.START:
            self.provider.mgmt.start_vm(self.name)
        elif option == EC2Instance.STOP:
            self.provider.mgmt.stop_vm(self.name)
        elif option == EC2Instance.RESTART:
            self.provider.mgmt.restart_vm(self.name)
        elif option == EC2Instance.TERMINATE:
            self.provider.mgmt.delete_vm(self.name)
        else:
            raise OptionNotAvailable(option + " is not a supported action")


###
# Multi-object functions
#
def _method_setup(vm_names, provider_crud=None):
    """ Reduces some redundant code shared between methods """
    if isinstance(vm_names, basestring):
        vm_names = [vm_names]

    if provider_crud:
        provider_crud.load_all_provider_instances()
    else:
        sel.force_navigate('clouds_instances')
    if paginator.page_controls_exist():
        paginator.results_per_page(1000)
    for vm_name in vm_names:
        sel.check(Quadicon(vm_name, 'instance').checkbox())


def find_quadicon(instance_name, do_not_navigate=False):
    """Find and return a quadicon belonging to a specific instance

    Args:
        instance_name: instance name as displayed at the quadicon
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
    if not do_not_navigate:
        sel.force_navigate('clouds_instances')
    if not paginator.page_controls_exist():
        raise InstanceNotFound("Instance '{}' not found in UI!".format(instance_name))

    paginator.results_per_page(1000)
    for page in paginator.pages():
        quadicon = Quadicon(instance_name, "instance")
        if sel.is_displayed(quadicon):
            return quadicon
    else:
        raise InstanceNotFound("Instance '{}' not found in UI!".format(instance_name))


def get_all_instances(do_not_navigate=False):
    """Returns list of all cloud instances"""
    if not do_not_navigate:
        sel.force_navigate('clouds_instances')
    vms = set([])
    if not paginator.page_controls_exist():
        return vms

    paginator.results_per_page(1000)
    for page in paginator.pages():
        try:
            for title in sel.elements(
                    "//div[@id='quadicon']/../../../tr/td/a[contains(@href,'vm_cloud/x_show')"
                    " or contains(@href, '/show/')]"):  # for provider specific vm/template page
                vms.add(sel.get_attribute(title, "title"))
        except sel.NoSuchElementException:
            pass
    return vms


def remove(instance_names, cancel=True, provider_crud=None):
    """Removes multiple instances from CFME VMDB

    Args:
        instance_names: List of instances to interact with
        cancel: Whether to cancel the deletion, defaults to True
        provider_crud: provider object where instances reside (optional)
    """
    _method_setup(instance_names, provider_crud)
    cfg_btn('Remove selected items from the VMDB', invokes_alert=True)
    sel.handle_alert(cancel=cancel)


def wait_for_instance_state_change(vm_name, desired_state, timeout=300, provider_crud=None):
    """Wait for an instance to come to desired state.

    This function waits just the needed amount of time thanks to wait_for.

    Args:
        vm_name: Displayed name of the instance
        desired_state: 'on' or 'off'
        timeout: Specify amount of time (in seconds) to wait until TimedOutError is raised
        provider_crud: provider object where instance resides (optional)
    """
    def _looking_for_state_change():
        toolbar.refresh()
        find_quadicon(vm_name, do_not_navigate=False).state == 'currentstate-' + desired_state

    _method_setup(vm_name, provider_crud)
    return wait_for(_looking_for_state_change, num_sec=timeout)


def is_pwr_option_visible(vm_names, option, provider_crud=None):
    """Returns whether a particular power option is visible.

    Args:
        vm_names: List of instances to interact with, if from_details=True is passed,
                  only one instance can be passed in the list.
        option: Power option param, see :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
        provider_crud: provider object where instance resides (optional)
    """
    _method_setup(vm_names, provider_crud)
    try:
        toolbar.is_greyed('Power', option)
        return True
    except sel.NoSuchElementException:
        return False


def is_pwr_option_enabled(vm_names, option, provider_crud=None):
    """Returns whether a particular power option is enabled

    Args:
        vm_names: List of instances to interact with
        provider_crud: provider object where vm resides on (optional)
        option: Power option param; for available power option, see
                :py:class:`EC2Instance` and :py:class:`OpenStackInstance`

    Raises:
        OptionNotAvailable: When unable to find the power option passed
    """
    _method_setup(vm_names, provider_crud)
    try:
        return not toolbar.is_greyed('Power', option)
    except sel.NoSuchElementException:
        raise OptionNotAvailable("No such power option (" + str(option) + ") is available")


def do_power_control(vm_names, option, provider_crud=None, cancel=True):
    """Executes a power option against a list of instances.

    Args:
        vm_names: List of instances to interact with
        option: Power option param; for available power options, see
                :py:class:`EC2Instance` and :py:class:`OpenStackInstance`
        provider_crud: provider object where instance resides (optional)
        cancel: Whether or not to cancel the power control action
    """
    _method_setup(vm_names, provider_crud)

    if (is_pwr_option_visible(vm_names, provider_crud=provider_crud, option=option) and
            is_pwr_option_enabled(vm_names, provider_crud=provider_crud, option=option)):
                pwr_btn(option, invokes_alert=True)
                sel.handle_alert(cancel=cancel)


@VM.register_for_provider_type("cloud")
class Image(Template):
    ALL_LIST_LOCATION = "clouds_images"
    TO_OPEN_EDIT = "Edit this Image"
    QUADICON_TYPE = "image"

    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper image details page.
        """
        locator = ("//div[@class='dhtmlxInfoBarLabel' and contains(. , 'Image \"%s\"')]" %
            self.name)

        # If the locator isn't on the page, or if it _is_ on the page and contains
        # 'Timelines' we are on the wrong page and take the appropriate action
        if not sel.is_displayed(locator):
            wrong_page = True
        else:
            wrong_page = 'Timelines' in sel.text(locator)

        if wrong_page:
            if not force:
                return False
            else:
                self.load_details()
                return True

        text = sel.text(locator).encode("utf-8")
        pattern = r'("[A-Za-z0-9_\./\\-]*")'
        import re
        m = re.search(pattern, text)

        if not force:
            return self.name == m.group().replace('"', '')
        else:
            if self.name != m.group().replace('"', ''):
                self.load_details()
                return True
            else:
                return True
