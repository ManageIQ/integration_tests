""" A model of Instances page in CFME."""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.common.vm import VM
from cfme.exceptions import InstanceNotFound, OptionNotAvailable, DestinationNotFound, \
    BlockTypeUnknown, TemplateNotFound, ToolbarOptionGreyedOrUnavailable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, paginator, toolbar as tb, CheckboxTree, Region, InfoBlock, \
    Tree, Quadicon, match_location, Form, Table, PagedTable, form_buttons
from cfme.web_ui.search import search_box
from utils import version
from utils.api import rest_api
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from utils.wait import wait_for
from utils.log import logger


cfg_btn = partial(tb.select, 'Configuration')
pwr_btn = partial(tb.select, 'Power')
life_btn = partial(tb.select, 'Lifecycle')
pol_btn = partial(tb.select, 'Policy')

tree_inst_by_prov = partial(accordion.tree, "Instances by Provider")
tree_instances = partial(accordion.tree, "Instances")
tree_image_by_prov = partial(accordion.tree, "Images by Provider")
tree_images = partial(accordion.tree, "Images")

list_page = Region(title='Instances')

policy_page = Region(
    locators={
        'policy_tree': Tree('//div[@class="containerTableStyle"]/table')
    })

image_select_form = Form(
    fields=[
        ('template_table', Table('//div[@id="pre_prov_div"]//table')),
        ('cancel_button', form_buttons.cancel)
    ]
)

manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

list_table = PagedTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='vm_cloud', title='Instances')


def details_page_check(name, provider):
    title_match = match_page(summary='Instance "{}"'.format(name))
    if title_match:
        # Also check provider
        try:
            prov_match = InfoBlock.text('Relationships', 'Cloud Provider') == provider.name
            return title_match and prov_match
        except BlockTypeUnknown:
            # Default to false since we can't identify which provider the image belongs to
            return False


@VM.register_for_provider_type("cloud")
class Instance(VM, Navigatable):
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
    TO_RETIRE = "Retire this Instance"
    QUADICON_TYPE = "instance"
    VM_TYPE = "Instance"

    REMOVE_SINGLE = {'5.6': 'Remove from the VMDB',
                     '5.7': 'Remove Instance'}

    def __init__(self, name, provider, template_name=None, appliance=None):
        super(Instance, self).__init__(name=name, provider=provider, template_name=template_name)
        Navigatable.__init__(self, appliance=appliance)

    def create(self):
        """Provisions an instance with the given properties through CFME
        """
        raise NotImplementedError('create is not implemented.')

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        # BZ 1389299
        # TODO: add refresh support back

    def get_detail(self, *args, **kwargs):
        # TODO: remove when bug 1389299 is fixed to use common.vm.get_detail()
        # Navigate to all first to force reload of details screen without using refresh
        navigate_to(self, 'All')
        self.load_details()
        if kwargs.get('icon_href', False):
            return InfoBlock.icon_href(*kwargs.get('properties'))
        else:
            return InfoBlock.text(*kwargs.get('properties'))

    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper instance details page.

           An instance may not be assigned to a provider if archived or orphaned
            If no provider is listed, default to False since we may be on the details page
            for an instance on the wrong provider.
        """

        if details_page_check(name=self.name, provider=self.provider):
            return True
        elif not force:
            return False
        elif force:
            navigate_to(self, 'Details')
            return True

    def get_vm_via_rest(self):
        # Try except block, because instances collection isn't available on 5.4
        try:
            instance = rest_api().collections.instances.get(name=self.name)
        except AttributeError:
            raise Exception("Collection instances isn't available")
        return instance

    def get_collection_via_rest(self):
        return rest_api().collections.instances

    def wait_for_instance_state_change(self, desired_state, timeout=900):
        """Wait for an instance to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: A string or list of strings indicating desired state
            timeout: Specify amount of time (in seconds) to wait until TimedOutError is raised
        """

        def _looking_for_state_change():
            current_state = self.get_detail(properties=("Power Management", "Power State"))
            logger.debug('Current Instance state: {}'.format(current_state))
            logger.debug('Desired Instance state: {}'.format(desired_state))
            if isinstance(desired_state, (list, tuple)):
                return current_state in desired_state
            else:
                return current_state == desired_state

        return wait_for(_looking_for_state_change, num_sec=timeout, delay=45,
                        message='Checking for instance state change',
                        fail_func=self.provider.refresh_provider_relationships())

    def find_quadicon(self, *args, **kwargs):
        """Find and return a quadicon belonging to a specific instance

        Args:
        Returns: :py:class:`cfme.web_ui.Quadicon` instance
        """
        if not kwargs.get('do_not_navigate', False):
            navigate_to(self, 'All')

        tb.select('Grid View')
        for page in paginator.pages():
            quadicon = Quadicon(self.name, "instance")
            if quadicon.exists:
                if kwargs.get('mark', False):
                    sel.check(quadicon.checkbox())
                return quadicon
        else:
            raise InstanceNotFound("Instance '{}' not found in UI!".format(self.name))

    def power_control_from_cfme(self, *args, **kwargs):
        """Power controls a VM from within CFME using instance details screen

        Raises:
            OptionNotAvailable: option param is not visible or enabled
        """
        # TODO push this to common.vm when infra and cloud have navmazing destinations

        if kwargs.get('from_details', True):
            navigate_to(self, 'Details')
        else:
            navigate_to(self, 'ProviderAll')
            self.find_quadicon(mark=True)
        if not kwargs.get('option'):
            raise ValueError('Need to provide option for power_control_from_cfme, no default.')
        try:
            if not pwr_btn(kwargs.get('option'), invokes_alert=True):
                raise ToolbarOptionGreyedOrUnavailable('Failed to click power button')
        except NoSuchElementException:
            raise OptionNotAvailable(kwargs.get('option') + " is not visible or enabled")

        sel.handle_alert(cancel=kwargs.get('cancel', False))


###
# Multi-object functions
###
def _method_setup(vm_names, provider_crud=None):
    """ Reduces some redundant code shared between methods """
    if isinstance(vm_names, basestring):
        vm_names = [vm_names]

    if provider_crud:
        provider_crud.load_all_provider_instances()
    else:
        navigate_to(Instance, 'All')
    if paginator.page_controls_exist():
        paginator.results_per_page(1000)
    for vm_name in vm_names:
        sel.check(Quadicon(vm_name, 'instance').checkbox())


def get_all_instances(do_not_navigate=False):
    """Returns list of all cloud instance names"""
    if not do_not_navigate:
        navigate_to(Instance, 'All')
    vms = set([])
    if not paginator.page_controls_exist():
        return vms

    # Cleaner to use list view and get names from rows than titles from Quadicons
    tb.select('List View')
    paginator.results_per_page(50)
    for page in paginator.pages():
        try:
            for row in list_table.rows():
                name = (row.__getattr__('Name')).text
                if name:
                    vms.add(name)
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
    cfg_btn(version.pick({
        version.LOWEST: 'Remove selected items from the VMDB',
        '5.7': 'Remove selected items'}), invokes_alert=True)
    sel.handle_alert(cancel=cancel)


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
        tb.is_greyed('Power', option)
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
        return not tb.is_greyed('Power', option)
    except sel.NoSuchElementException:
        raise OptionNotAvailable("No such power option (" + str(option) + ") is available")


def select_provision_image(template_name, provider):
    """
    Navigate to provision and select the template+click continue, leaving UI on provision form

    :param template_name: The image/template name to select
    :param provider: Provider where the image/template resides
    :return: none
    """
    logger.debug('Selecting an image {} from provider {} for provisioning'
                 .format(template_name, provider.name))
    navigate_to(Instance, 'Provision')
    template = image_select_form.template_table.find_row_by_cells({
        'Name': template_name,
        'Provider': provider.name
    })
    if template:
        sel.click(template)
        # In order to mitigate the sometimes very long spinner timeout, raise the timeout
        with sel.ajax_timeout(90):
            sel.click(form_buttons.FormButton("Continue", force_click=True))

    else:
        raise TemplateNotFound('Unable to find template "{}" for provider "{}"'.format(
            template_name, provider.key))


@navigator.register(Instance, 'All')
class InstanceAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Instances')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Instances')(None)

        # use accordion
        # If a filter was applied, it will persist through navigation and needs to be cleared
        if sel.is_displayed(search_box.clear_advanced_search):
            logger.debug('Clearing advanced search filter')
            sel.click(search_box.clear_advanced_search)
        accordion.tree('Instances', 'All Instances')


@navigator.register(Instance, 'ProviderAll')
class InstanceProviderAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Instances under Provider "{}"'.format(self.obj.provider.name))

    def step(self, *args, **kwargs):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Instances')(None)

        # use accordion
        # If a filter was applied, it will persist through navigation and needs to be cleared
        if sel.is_displayed(search_box.clear_advanced_search):
            logger.debug('Clearing advanced search filter')
            sel.click(search_box.clear_advanced_search)
        accordion.tree('Instances by Provider', 'Instances by Provider', self.obj.provider.name)


@navigator.register(Instance, 'Details')
class InstanceDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return details_page_check(name=self.obj.name, provider=self.obj.provider)

    def step(self):
        # Use list view to match name and provider
        tb.select('List View')
        # Instance may be in a state where the provider is not displayed in the table
        # Try first to match name and provider, fall back to just name
        # Matching only on name has the potential to select the wrong instance
        try:
            return sel.click(list_table.find_row_by_cell_on_all_pages(
                {'Name': self.obj.name,
                 'Provider': self.obj.provider.name}))
        except (NameError, TypeError):
            logger.warning('Exception caught, could not match instance with name and provider')

        # If name and provider weren't matched, look for just name
        logger.warning('Matching instance only using name only: {}'.format(self.obj.name))
        sel.click(list_table.find_row_by_cell_on_all_pages({'Name': self.obj.name}))


@navigator.register(Instance, 'Provision')
class InstanceProvision(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='Provision Instances - Select an Image')

    def step(self):
        life_btn('Provision Instances')


@navigator.register(Instance, 'Edit')
class InstanceEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Edit this instance')


@navigator.register(Instance, 'SetOwnership')
class InstanceOwnership(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Set Ownership')


@navigator.register(Instance, 'EditMgmtEngineRelation')
class InstanceEditMgmtEngineRelation(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Edit Management Engine Relationship')


@navigator.register(Instance, 'AttachCloudVolume')
class InstanceAttachVolume(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Attach a Cloud Volume to this instance')


@navigator.register(Instance, 'DetachCloudVolume')
class InstanceDetachVolume(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Detach a Cloud Volume to this instance')


@navigator.register(Instance, 'Reconfigure')
class InstanceReconfigure(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Reconfigure this Instance')


@navigator.register(Instance, 'RightSize')
class InstanceRightSize(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        cfg_btn('Right-Size Recommendations')


@navigator.register(Instance, 'AddFloatingIP')
class InstanceAddFloatingIP(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        if version.current_version() >= '5.7':
            cfg_btn('Associate a Floating IP with this Instance')
        else:
            raise DestinationNotFound('Floating IP assignment not available for appliance version')


@navigator.register(Instance, 'RemoveFloatingIP')
class InstanceRemoveFloatingIP(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self):
        if version.current_version() >= '5.7':
            cfg_btn('Disassociate a Floating IP from this Instance')
        else:
            raise DestinationNotFound('Floating IP assignment not available for appliance version')
