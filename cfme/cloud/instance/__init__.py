from time import sleep

from navmazing import NavigateToSibling, NavigateToAttribute
from riggerlib import recursive_update
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View, Text
from widgetastic_patternfly import Dropdown, Button, FlashMessages
from widgetastic_manageiq import (
    Accordion, ManageIQTree, Table, PaginationPane, TimelinesView, SummaryTable,
    ItemsToolBarViewSelector, Search)

from cfme.base.login import BaseLoggedInPage
from cfme.common.vm import VM, EditServerRelationShipView
from cfme.exceptions import InstanceNotFound, DestinationNotFound, TemplateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.provisioning import ProvisioningForm
from cfme.web_ui import flash, Quadicon, match_location
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from utils.log import logger
from utils.wait import wait_for


class InstanceToolbar(View):
    reload = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    power = Dropdown('Power Operations')  # title
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class InstanceDetailsToolbar(View):
    reload = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    monitoring = Dropdown('Monitoring')
    power = Dropdown('Instance Power Functions')  # title
    download = Button(title='Download summary in PDF format')


# For all instance views (all, details, etc)
class InstanceAccordion(View):
    @View.nested
    class instances_by_provider(Accordion):  # noqa
        ACCORDION_NAME = 'Instances by Provider'
        tree = ManageIQTree()

    @View.nested
    class images_by_provider(Accordion):  # noqa
        ACCORDION_NAME = 'Images by Provider'
        tree = ManageIQTree()

    @View.nested
    class instances(Accordion):  # noqa
        ACCORDION_NAME = 'Instances'
        tree = ManageIQTree()

    @View.nested
    class images(Accordion):  # noqa
        ACCORDION_NAME = 'Images'
        tree = ManageIQTree()


class InstanceEntities(View):
    title = Text('//div[@id="main-content"]//h1//span[@id="explorer_title_text"]')
    adv_search_clear = Text('//div[@id="main-content"]//h1//span[@id="clear_search"]/a')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')
    search = View.nested(Search)
    table = Table("//div[@id='list_grid']//table")


class InstanceDetailsEntities(View):
    title = Text('//div[@id="main-content"]//h1//span[@id="explorer_title_text"]')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')
    properties = SummaryTable(title='Properties')
    lifecycle = SummaryTable(title='Lifecycle')
    relationships = SummaryTable(title='Relationships')
    vmsafe = SummaryTable(title='VMsafe')
    labels = SummaryTable(title='Labels')
    compliance = SummaryTable(title='Compliance')
    power_management = SummaryTable(title='Power Management')
    security = SummaryTable(title='Security')
    configuration = SummaryTable(title='Configuration')
    diagnostics = SummaryTable(title='Diagnostics')
    smart_management = SummaryTable(title='Smart Management')


class CloudInstanceView(BaseLoggedInPage):
    """Base view for header/nav check, inherit for navigatable views"""
    @property
    def in_cloud_instance(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Compute', 'Clouds', 'Instances'] and
                match_location(controller='vm_cloud', title='Instances'))


class InstanceAllView(CloudInstanceView):
    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'All Instances' and
            self.sidebar.instances.is_opened)

    toolbar = View.nested(InstanceToolbar)
    sidebar = View.nested(InstanceAccordion)
    entities = View.nested(InstanceEntities)
    paginator = View.nested(PaginationPane)


class InstanceProviderAllView(CloudInstanceView):
    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'Instances under Provider "{}"'
                               .format(self.context['object'].provider.name) and
            self.sidebar.instances_by_provider.is_opened)

    toolbar = View.nested(InstanceToolbar)
    sidebar = View.nested(InstanceAccordion)
    entities = View.nested(InstanceEntities)
    paginator = View.nested(PaginationPane)


class InstanceDetailsView(CloudInstanceView):
    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        expected_provider = self.context['object'].provider.name
        try:
            # Not displayed when the instance is archived
            relationship_provider_name = self.relationships_detail.get_text_of('Cloud Provider')
        except NameError:
            logger.warning('No "Cloud Provider" Relationship, assume instance view not displayed')
            return False
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'Instance "{}"'.format(expected_name) and
            relationship_provider_name == expected_provider)

    toolbar = View.nested(InstanceDetailsToolbar)
    sidebar = View.nested(InstanceAccordion)
    entities = View.nested(InstanceDetailsEntities)


class ProvisionView(CloudInstanceView):
    title = Text('#explorer_title_text')

    @View.nested
    class form(ProvisioningForm):  # noqa
        image_table = Table('//div[@id="pre_prov_div"]//table')
        continue_button = Button('Continue')  # Continue button on 1st page, image selection
        submit_button = Button('Submit')  # Submit for 2nd page, tabular form
        cancel_button = Button('Cancel')

        def before_fill(self, values):
            # Provision from image is a two part form,
            # this completes the image selection before the tabular parent form is filled
            template_name = values.get('template_name',
                                       self.parent_view.context['object'].template_name)
            provider_name = self.parent_view.context['object'].provider.name
            try:
                row = self.image_table.row(name=template_name,
                                           provider=provider_name)
            except IndexError:
                raise TemplateNotFound('Cannot find template "{}" for provider "{}"'
                                       .format(template_name, provider_name))
            row.click()
            self.continue_button.click()
            # TODO timing, wait_displayed is timing out and can't get it to stop in is_displayed
            sleep(3)
            self.flush_widget_cache()

    @property
    def is_displayed(self):
        return False

class InstanceTimelinesView(CloudInstanceView, TimelinesView):
    @property
    def is_displayed(self):
        return (
            super(CloudInstanceView, self).in_cloud_instance and
            super(TimelinesView, self).is_displayed)


class Instance(VM, Navigatable):
    """Represents a generic instance in CFME. This class is used if none of the inherited classes
    will match.

    Args:
        name: Name of the instance
        provider: :py:class:`cfme.cloud.provider.Provider` object
        template_name: Name of the template to use for provisioning
        appliance: :py:class: `utils.appliance.IPAppliance` object
    Note:
        This class cannot be instantiated. Use :py:func:`instance_factory` instead.
    """
    ALL_LIST_LOCATION = "clouds_instances"
    TO_RETIRE = "Retire this Instance"
    QUADICON_TYPE = "instance"
    VM_TYPE = "Instance"
    PROVISION_CANCEL = 'Add of new VM Provision Request was cancelled by the user'
    PROVISION_START = ('VM Provision Request was Submitted, you will be notified when your VMs '
                       'are ready')

    REMOVE_SINGLE = 'Remove Instance'

    TO_OPEN_EDIT = "Edit this Instance"

    def __init__(self, name, provider, template_name=None, appliance=None):
        super(Instance, self).__init__(name=name, provider=provider, template_name=template_name)
        Navigatable.__init__(self, appliance=appliance)

    def create(self, form_values, cancel=False):
        """Provisions an instance with the given properties through CFME

        Args:
            form_values: dictionary of form values for provisioning, structured into tabs

        Note:
            Calling create on a sub-class of instance will generate the properly formatted
            dictionary when the correct fields are supplied.
        """
        view = navigate_to(self, 'Provision')

        # Only support 1 security group for now
        # TODO: handle multiple
        if 'environment' in form_values and 'security_groups' in form_values['environment'] and \
                isinstance(form_values['environment']['security_groups'], (list, tuple)):

            first_group = form_values['environment']['security_groups'][0]
            recursive_update(form_values, {'environment': {'security_groups': first_group}})

        view.form.fill(form_values)

        if cancel:
            view.form.cancel_button.click()
            # Redirects to Instance All
            view = self.browser.create_view(InstanceAllView)
            wait_for(lambda: view.is_displayed, timeout=10, delay=2, message='wait for redirect')
            view.entities.flash.assert_success_message(self.PROVISION_CANCEL)
            view.entities.flash.assert_no_error()
        else:
            view.form.submit_button.click()
            # TODO this redirects to service.request, create_view on it when it exists for flash
            wait_for(flash.get_messages, fail_condition=[], timeout=10, delay=2,
                     message='wait for Flash Success')
            flash.assert_success_message(self.PROVISION_START)

    def update(self, values, cancel=False, reset=False):
        """Update cloud instance

        Args:
            values: Dictionary of form key/value pairs
            cancel: Boolean, cancel the form submission
            reset Boolean, reset form after fill - returns immediately after reset
        Note:
            The edit form contains a 'Reset' button - if this is c
        """
        view = navigate_to(self, 'Edit')
        # form is the view's parent
        view.form.fill(values)
        if reset:
            view.form.reset_button.click()
            return
        else:
            button = view.form.cancel_button if cancel else view.form.submit_button
            button.click()

    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper instance details page.

           An instance may not be assigned to a provider if archived or orphaned
            If no provider is listed, default to False since we may be on the details page
            for an instance on the wrong provider.
        """
        if not force:
            return self.browser.create_view(InstanceDetailsView).is_displayed
        else:
            navigate_to(self, 'Details')
            return True

    def get_vm_via_rest(self):
        # Try except block, because instances collection isn't available on 5.4
        try:
            instance = self.appliance.rest_api.collections.instances.get(name=self.name)
        except AttributeError:
            raise Exception("Collection instances isn't available")
        else:
            return instance

    def get_collection_via_rest(self):
        return self.appliance.rest_api.collections.instances

    def wait_for_instance_state_change(self, desired_state, timeout=900):
        """Wait for an instance to come to desired state.

        This function waits just the needed amount of time thanks to wait_for.

        Args:
            desired_state: A string or list of strings indicating desired state
            timeout: Specify amount of time (in seconds) to wait until TimedOutError is raised
        """

        def _looking_for_state_change():
            view = navigate_to(self, 'Details')
            current_state = view.entities.power_management.get_text_of("Power State")
            logger.debug('Current Instance state: {}'.format(current_state))
            logger.debug('Desired Instance state: {}'.format(desired_state))
            if isinstance(desired_state, (list, tuple)):
                return current_state in desired_state
            else:
                return current_state == desired_state

        return wait_for(_looking_for_state_change, num_sec=timeout, delay=45,
                        message='Checking for instance state change',
                        fail_func=self.provider.refresh_provider_relationships)

    def find_quadicon(self, **kwargs):
        """Find and return a quadicon belonging to a specific instance

        Args:
        Returns: :py:class:`cfme.web_ui.Quadicon` instance
        """
        # TODO refactor a bit when quadicon is widget
        if not kwargs.get('do_not_navigate', False):
            navigate_to(self, 'All')

        # Make sure we're looking at the quad grid
        view = self.browser.create_view(InstanceAllView)
        view.toolbar.view_selector.select('Grid View')
        for _ in view.paginator.pages():
            quadicon = Quadicon(self.name, "instance")
            if quadicon.exists:
                if kwargs.get('mark', False):
                    sel.check(quadicon.checkbox())
                return quadicon
        else:
            raise InstanceNotFound("Instance '{}' not found in UI!".format(self.name))

    def power_control_from_cfme(self, *args, **kwargs):
        """Power controls a VM from within CFME using details or collection

        Raises:
            InstanceNotFound: the instance wasn't found when navigating
            OptionNotAvailable: option param is not visible or enabled
        """
        # TODO push this to common.vm when infra vm classes have widgets
        if not kwargs.get('option'):
            raise ValueError('Need to provide option for power_control_from_cfme, no default.')

        if kwargs.get('from_details', True):
            view = navigate_to(self, 'Details')
        else:
            view = navigate_to(self, 'AllForProvider')
            view.toolbar.view_selector.select('List View')
            try:
                row = view.paginator.find_row_on_pages(view.entities.table, name=self.name)
            except NoSuchElementException:
                raise InstanceNotFound('Failed to find instance in table: {}'.format(self.name))
            row[0].check()

        # cancel is the kwarg, when true we want item_select to dismiss the alert, flip the bool
        view.toolbar.power.item_select(kwargs.get('option'),
                                       handle_alert=not kwargs.get('cancel', False))


@navigator.register(Instance, 'All')
class All(CFMENavigateStep):
    VIEW = InstanceAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Instances')
        self.view.sidebar.instances.tree.click_path('All Instances')

    def resetter(self, *args, **kwargs):
        # If a filter was applied, it will persist through navigation and needs to be cleared
        if self.view.entities.adv_search_clear.is_displayed:
            logger.debug('Clearing advanced search filter')
            self.view.entities.adv_search_clear.click()
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'AllForProvider')
class AllForProvider(CFMENavigateStep):
    VIEW = InstanceProviderAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Instances')
        self.view.sidebar.instances_by_provider.tree.click_path('Instances by Provider',
                                                                self.obj.provider.name)

    def resetter(self, *args, **kwargs):
        # If a filter was applied, it will persist through navigation and needs to be cleared
        if self.view.entities.adv_search_clear.is_displayed:
            logger.debug('Clearing advanced search filter')
            self.view.entities.adv_search_clear.click()
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'AddFloatingIP')
class AddFloatingIP(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        if version.current_version() >= '5.7':
            try:
                self.prerequisite_view.toolbar.configuration.item_select(
                    'Associate a Floating IP with this Instance')
            except NoSuchElementException:
                raise DestinationNotFound('Add Floating IP option not available for instance')
        else:
            raise DestinationNotFound('Floating IP assignment not available for appliance version')


@navigator.register(Instance, 'Details')
class Details(CFMENavigateStep):
    VIEW = InstanceDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        # Use list view to match name and provider
        self.prerequisite_view.toolbar.view_selector.select('List View')
        # Instance may be in a state where the provider is not displayed in the table
        # Try first to match name and provider, fall back to just name
        # Matching only on name has the potential to select the wrong instance

        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name,
                provider=self.obj.provider.name)
            self.log_message('Matched table row on instance name and provider')
        except NoSuchElementException:
            logger.warning('Could not match instance row using name "{}" and provider "{}"'
                           .format(self.obj.name,
                                   self.obj.provider.name))
            row = None
        if not row:
            logger.warning('Attempting to match instance using name only: "{}"'
                           .format(self.obj.name))
            try:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table, name=self.obj.name)
                self.log_message('Matched table row on instance name only')
            except NoSuchElementException:
                raise InstanceNotFound('Could not match instance by name only: {}'
                                       .format(self.obj.name))

        if row:
            row.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Instance')


@navigator.register(Instance, 'EditMgmtEngineRelation')
class EditMgmtEngineRelation(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Edit Management Engine Relationship')


@navigator.register(Instance, 'Provision')
class Provision(CFMENavigateStep):
    VIEW = ProvisionView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Provision Instances')


@navigator.register(Instance, 'Reconfigure')
class Reconfigure(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self):
        try:
            self.prerequisite_view.toolbar.configuration.item_select('Reconfigure this Instance')
        except NoSuchElementException:
            raise DestinationNotFound('Reconfigure option not available for instance')


@navigator.register(Instance, 'RightSize')
class RightSize(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self):
        try:
            self.prerequisite_view.toolbar.configuration.item_select('Right-Size Recommendations')
        except NoSuchElementException:
            raise DestinationNotFound('Right Size option not available for instance')


@navigator.register(Instance, 'RemoveFloatingIP')
class RemoveFloatingIP(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        if version.current_version() >= '5.7':
            try:
                self.prerequisite_view.toolbar.configuration.item_select(
                    'Disassociate a Floating IP from this Instance')
            except NoSuchElementException:
                raise DestinationNotFound('Remove Floating IP option not available for instance')
        else:
            raise DestinationNotFound('Floating IP assignment not available for appliance version')


@navigator.register(Instance, 'SetOwnership')
class SetOwnership(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(Instance, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = InstanceTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Instance, 'EditManagementEngineRelationship')
class VmEngineRelationship(CFMENavigateStep):
    VIEW = EditServerRelationShipView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit Management Engine Relationship')
