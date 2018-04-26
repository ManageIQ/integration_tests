from navmazing import NavigateToSibling, NavigateToAttribute
from riggerlib import recursive_update
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import CheckableBootstrapTreeview, Dropdown, Button
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View

from cfme.base.login import BaseLoggedInPage
from cfme.common.candu_views import AzureInstanceUtilizationView, Ec2InstanceUtilizationView
from cfme.common.vm import VM
from cfme.common.vm_views import (
    ProvisionView, VMToolbar, VMEntities, VMDetailsEntities, EditView,
    SetOwnershipView, ManagementEngineView, PolicySimulationView,
    RetirementView, RetirementViewWithOffset)
from cfme.exceptions import InstanceNotFound, ItemNotFound
from cfme.services.requests import RequestsView
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from widgetastic_manageiq import ManageIQTree, TimelinesView, Accordion, CompareToolBarActionsView


class InstanceDetailsToolbar(View):
    """
    The toolbar on the details screen for an instance
    """
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    monitoring = Dropdown('Monitoring')
    power = Dropdown('Instance Power Functions')  # title
    download = Button(title='Download summary in PDF format')
    access = Dropdown("Access")


class InstanceAccordion(View):
    """
    The accordion on the instances page
    """
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


class InstanceCompareAccordion(View):
    """
    The accordion on the instance comparison page
    """
    @View.nested
    class comparison_sections(Accordion):  # noqa
        ACCORDION_NAME = 'Comparison Sections'
        tree = CheckableBootstrapTreeview()

    apply = Button('Apply')


class CloudInstanceView(BaseLoggedInPage):
    """Base view for header/nav check, inherit for navigatable views"""
    @property
    def in_cloud_instance(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Instances']
        )


class InstanceAllView(CloudInstanceView):
    """
    The collection page for instances
    """
    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'All Instances' and
            self.sidebar.instances.is_opened)

    actions = View.nested(CompareToolBarActionsView)
    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(InstanceAccordion)
    including_entities = View.include(VMEntities, use_parent=True)


class InstanceProviderAllView(CloudInstanceView):
    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'Instances under Provider "{}"'
                               .format(self.context['object'].provider.name) and
            self.sidebar.instances_by_provider.is_opened)

    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(InstanceAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @View.nested
    class instances_by_provider(Accordion):  # noqa
        ACCORDION_NAME = 'Instances by Provider'
        tree = ManageIQTree()


class InstanceDetailsView(CloudInstanceView):
    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        expected_provider = self.context['object'].provider.name
        try:
            # Not displayed when the instance is archived
            relationships = self.entities.summary('Relationships')
            relationship_provider_name = relationships.get_text_of('Cloud Provider')
        except (NameError, NoSuchElementException):
            logger.warning('No "Cloud Provider" Relationship, assume instance view not displayed')
            return False
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'Instance "{}"'.format(expected_name) and
            relationship_provider_name == expected_provider)

    toolbar = View.nested(InstanceDetailsToolbar)
    sidebar = View.nested(InstanceAccordion)
    entities = View.nested(VMDetailsEntities)


class InstanceTimelinesView(TimelinesView, CloudInstanceView):
    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        return (
            self.in_cloud_instance and
            self.title.text == 'Timelines for Instance "{}"'.format(expected_name))


class InstanceCompareView(CloudInstanceView):
    """
    The comparison page for instances
    """
    @property
    def is_displayed(self):
        return self.in_cloud_instance and self.entities.title.text == 'Compare VM or Template'

    toolbar = View.nested(CompareToolBarActionsView)
    sidebar = View.nested(InstanceCompareAccordion)


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
    DETAILS_VIEW_CLASS = InstanceDetailsView

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
            view.flash.assert_success_message(self.PROVISION_CANCEL)
            view.flash.assert_no_error()
        else:
            view.form.submit_button.click()

            view = self.appliance.browser.create_view(RequestsView)
            wait_for(lambda: view.flash.messages, fail_condition=[], timeout=10, delay=2,
                     message='wait for Flash Success')
            view.flash.assert_success_message(self.PROVISION_START)

    def update(self, values, cancel=False, reset=False):
        """Update cloud instance

        Args:
            values: Dictionary of form key/value pairs
            cancel: Boolean, cancel the form submission
            reset: Boolean, reset form after fill - returns immediately after reset
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
            current_state = view.entities.summary("Power Management").get_text_of("Power State")
            logger.info('Current Instance state: {}'.format(current_state))
            logger.info('Desired Instance state: {}'.format(desired_state))
            if isinstance(desired_state, (list, tuple)):
                return current_state in desired_state
            else:
                return current_state == desired_state

        return wait_for(_looking_for_state_change, num_sec=timeout, delay=15,
                        message='Checking for instance state change',
                        fail_func=self.provider.refresh_provider_relationships,
                        handle_exception=True)

    def find_quadicon(self, **kwargs):
        """Find and return a quadicon belonging to a specific instance

        TODO: remove this method and refactor callers to use view entities instead

        Args:
        Returns: entity of appropriate type
        """
        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('Grid View')

        try:
            return view.entities.get_entity(name=self.name, surf_pages=True)
        except ItemNotFound:
            raise InstanceNotFound("Instance '{}' not found in UI!".format(self.name))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except InstanceNotFound:
            return False

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
                row = view.entities.get_entity(name=self.name)
            except ItemNotFound:
                raise InstanceNotFound('Failed to find instance in table: {}'.format(self.name))
            row.check()

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
        self.view.entities.search.remove_search_filters()
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
        if self.view.adv_search_clear.is_displayed:
            logger.debug('Clearing advanced search filter')
            self.view.adv_search_clear.click()
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'Details')
class Details(CFMENavigateStep):
    VIEW = InstanceDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True,
                                                             use_search=True)
        except ItemNotFound:
            raise InstanceNotFound('Failed to locate instance with name "{}"'.format(self.obj.name))
        row.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'ArchiveDetails')
class ArchiveDetails(CFMENavigateStep):
    VIEW = InstanceDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True,
                                                             use_search=True)
        except ItemNotFound:
            raise InstanceNotFound('Failed to locate instance with name "{}"'.format(self.obj.name))
        row.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = EditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Instance')


@navigator.register(Instance, 'EditManagementEngineRelationship')
class EditManagementEngineRelationship(CFMENavigateStep):
    VIEW = ManagementEngineView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        configuration = self.prerequisite_view.toolbar.configuration
        configuration.item_select('Edit Management Engine Relationship')


@navigator.register(Instance, 'Provision')
class Provision(CFMENavigateStep):
    VIEW = ProvisionView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Provision Instances')


@navigator.register(Instance, 'PolicySimulation')
class PolicySimulation(CFMENavigateStep):
    VIEW = PolicySimulationView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Policy Simulation')


@navigator.register(Instance, 'SetOwnership')
class SetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(Instance, 'SetRetirement')
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


@navigator.register(Instance, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = InstanceTimelinesView
    prerequisite = NavigateToSibling('ArchiveDetails')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Instance, 'candu')
class InstanceUtilization(CFMENavigateStep):
    @property
    def get_view(self):
        """Property returning VM Utilization Views as per provider type"""
        if self.obj.provider.type is 'azure':
            view = AzureInstanceUtilizationView
        elif self.obj.provider.type is 'ec2':
            view = Ec2InstanceUtilizationView
        else:
            view = None
        return view

    VIEW = get_view
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
