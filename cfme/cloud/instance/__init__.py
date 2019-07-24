import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from navmazing import NavigationDestinationNotFound
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import partial_match
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import CheckableBootstrapTreeview
from widgetastic_patternfly import Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.common import TimelinesView
from cfme.common.vm import VM
from cfme.common.vm import VMCollection
from cfme.common.vm_views import EditView
from cfme.common.vm_views import ManagementEngineView
from cfme.common.vm_views import PolicySimulationView
from cfme.common.vm_views import ProvisionView
from cfme.common.vm_views import RetirementViewWithOffset
from cfme.common.vm_views import SetOwnershipView
from cfme.common.vm_views import VMDetailsEntities
from cfme.common.vm_views import VMEntities
from cfme.common.vm_views import VMToolbar
from cfme.exceptions import DestinationNotFound
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import CompareToolBarActionsView
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class InstanceDetailsToolbar(View):
    """
    The toolbar on the details screen for an instance
    """
    reload = Button(title='Refresh this page')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    monitoring = Dropdown('Monitoring')
    power = Dropdown('Instance Power Functions')  # title
    download = Button(title='Print or export summary')
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
    search = View.nested(Search)
    including_entities = View.include(VMEntities, use_parent=True)


class InstanceProviderAllView(CloudInstanceView):
    @property
    def is_displayed(self):
        try:
            provider = self.context['object'].filters.get('provider').name
        except AttributeError:
            provider = self.context['object'].provider.name
        return (
            self.in_cloud_instance and
            self.entities.title.text == 'Instances under Provider "{}"'
                               .format(provider) and
            self.sidebar.instances_by_provider.is_opened)

    toolbar = View.nested(VMToolbar)
    sidebar = View.nested(InstanceAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @View.nested
    class instances_by_provider(Accordion):  # noqa
        ACCORDION_NAME = 'Instances by Provider'
        tree = ManageIQTree()


class InstanceDetailsView(CloudInstanceView):
    tag = SummaryTable(title='Smart Management')

    @property
    def is_displayed(self):
        expected_name = self.context['object'].name
        expected_provider = self.context['object'].provider.name
        try:
            # Not displayed when the instance is archived
            relationships = self.entities.summary('Relationships')
            relationship_provider_name = relationships.get_text_of('Cloud Provider')
            return (
                self.in_cloud_instance and
                self.entities.title.text == 'Instance "{}"'.format(expected_name) and
                relationship_provider_name == expected_provider
            )
        except (NameError, NoSuchElementException):
            logger.warning('No "Cloud Provider" Relationship, assume instance view not displayed')
            # for archived instances the relationship_provider_name is removed from the summary
            # table
            return (
                self.in_cloud_instance and
                self.entities.title.text == 'Instance "{}"'.format(expected_name)
            )

    toolbar = View.nested(InstanceDetailsToolbar)
    sidebar = View.nested(InstanceAccordion)
    entities = View.nested(VMDetailsEntities)


class InstanceTimelinesView(TimelinesView, CloudInstanceView):

    @property
    def is_displayed(self):
        if self.breadcrumb.is_displayed:
            check_object = self.breadcrumb.locations
        else:
            # since in 5.10 there is no breadcrumb
            check_object = self.title.text

        return (
            self.context['object'].name in check_object and
            # this last check is less specific due to BZ 1732517
            "Timeline" in self.title.text
        )


class InstanceCompareView(CloudInstanceView):
    """
    The comparison page for instances
    """
    @property
    def is_displayed(self):
        return self.in_cloud_instance and self.entities.title.text == 'Compare VM or Template'

    toolbar = View.nested(CompareToolBarActionsView)
    sidebar = View.nested(InstanceCompareAccordion)


@attr.s
class Instance(VM):
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

    REMOVE_SINGLE = 'Remove Instance'
    TO_OPEN_EDIT = "Edit this Instance"
    DETAILS_VIEW_CLASS = InstanceDetailsView

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
        view = navigate_to(self.parent, 'All')
        view.toolbar.view_selector.select('Grid View')

        try:
            return view.entities.get_entity(name=self.name, surf_pages=True)
        except ItemNotFound:
            raise ItemNotFound("Instance '{}' not found in UI!".format(self.name))

    def power_control_from_cfme(self, *args, **kwargs):
        """Power controls a VM from within CFME using details or collection

        Raises:
            ItemNotFound: the instance wasn't found when navigating
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
                row = view.entities.get_entity(name=self.name, surf_pages=True)
            except ItemNotFound:
                raise ItemNotFound(
                    'Failed to find instance in table: {}'.format(self.name)
                )
            row.check()

        # cancel is the kwarg, when true we want item_select to dismiss the alert, flip the bool
        view.toolbar.power.item_select(kwargs.get('option'),
                                       handle_alert=not kwargs.get('cancel', False))

    @property
    def vm_default_args(self):
        """Represents dictionary used for Vm/Instance provision with minimum required default args
        """
        provisioning = self.provider.data['provisioning']
        inst_args = {
            'request': {'email': 'vm_provision@cfmeqe.com'},
            'catalog': {
                'vm_name': self.name},
            'environment': {
                'availability_zone': provisioning.get('availability_zone'),
                'cloud_network': provisioning.get('cloud_network'),
                'cloud_subnet': provisioning.get('cloud_subnet'),
                'resource_groups': provisioning.get('resource_group')
            },
            'properties': {
                'instance_type': partial_match(provisioning.get('instance_type')),
                'guest_keypair': provisioning.get('guest_keypair')
            }
        }

        return inst_args

    @property
    def vm_default_args_rest(self):
        """Represents dictionary used for REST API Instance provision with minimum required default
        args
        """
        from cfme.cloud.provider.azure import AzureProvider
        from cfme.cloud.provider.ec2 import EC2Provider

        if not self.provider.is_refreshed():
            self.provider.refresh_provider_relationships()
            wait_for(self.provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        provisioning = self.provider.data['provisioning']

        provider_rest = self.appliance.rest_api.collections.providers.get(name=self.provider.name)

        # find out image guid
        image_name = provisioning['image']['name']
        image = self.appliance.rest_api.collections.templates.get(name=image_name,
                                                                  ems_id=provider_rest.id)
        # find out flavor
        if ':' in provisioning['instance_type'] and self.provider.one_of(EC2Provider):
            instance_type = provisioning['instance_type'].split(':')[0].strip()
        else:
            instance_type = provisioning['instance_type']
        flavor = self.appliance.rest_api.collections.flavors.get(name=instance_type,
                                                                 ems_id=provider_rest.id)
        # find out cloud network
        cloud_network_name = provisioning.get('cloud_network').strip()
        if self.provider.one_of(EC2Provider, AzureProvider):
            cloud_network_name = cloud_network_name.split()[0]
        cloud_network = self.appliance.rest_api.collections.cloud_networks.get(
            name=cloud_network_name, enabled='true')
        # find out cloud subnet
        cloud_subnet = self.appliance.rest_api.collections.cloud_subnets.get(
            cloud_network_id=cloud_network['id'])
        # find out availability zone
        azone_id = None
        av_zone_name = provisioning.get('availability_zone')
        if av_zone_name:
            azone_id = self.appliance.rest_api.collections.availability_zones.get(
                name=av_zone_name, ems_id=flavor.ems_id).id
        # find out cloud tenant
        tenant_name = provisioning.get('cloud_tenant')
        if tenant_name:
            try:
                tenant = self.appliance.rest_api.collections.cloud_tenants.get(
                    name=tenant_name,
                    ems_id=provider_rest.id,
                    enabled='true')
            except IndexError:
                raise ItemNotFound("Tenant {} not found on provider {}".format(
                    tenant_name, self.provider.name))

        resource_group_id = None
        if self.provider.one_of(AzureProvider):
            resource_groups = self.appliance.rest_api.get(
                '{}?attributes=resource_groups'.format(provider_rest._href))['resource_groups']
            resource_group_id = None
            resource_group_name = provisioning.get('resource_group')
            for res_group in resource_groups:
                if (res_group['name'] == resource_group_name and
                        res_group['ems_id'] == provider_rest.id):
                    resource_group_id = res_group['id']
                    break

        inst_args = {
            "version": "1.1",
            "template_fields": {
                "guid": image.guid
            },
            "vm_fields": {
                "placement_auto": False,
                "vm_name": self.name,
                "instance_type": flavor['id'],
                "request_type": "template",
                "cloud_network": cloud_network['id'],
                "cloud_subnet": cloud_subnet['id'],

            },
            "requester": {
                "user_name": "admin",
                "owner_email": "admin@example.com",
                "auto_approve": True,
            },
            "tags": {
            },
            "ems_custom_attributes": {
            },
            "miq_custom_attributes": {
            }
        }
        if tenant_name:
            inst_args['vm_fields']['cloud_tenant'] = tenant['id']
        if resource_group_id:
            inst_args['vm_fields']['resource_group'] = resource_group_id
        if azone_id:
            inst_args['vm_fields']['placement_availability_zone'] = azone_id
        if self.provider.one_of(EC2Provider):
            inst_args['vm_fields']['monitoring'] = 'basic'

        return inst_args


@attr.s
class InstanceCollection(VMCollection):
    ENTITY = Instance

    def all(self):
        """Return entities for all items in collection"""
        # Pretty much same as image, but defining at VMCollection would only work for cloud
        # provider filter means we're viewing instances through provider details relationships
        provider = self.filters.get('provider')  # None if no filter, need for entity instantiation
        view = navigate_to(provider or self,
                          'Instances' if provider else 'All')
        # iterate pages here instead of use surf_pages=True because data is needed
        entities = []
        for _ in view.entities.paginator.pages():  # auto-resets to first page
            page_entities = [entity for entity in view.entities.get_all(surf_pages=False)]
            entities.extend(
                # when provider filtered view, there's no provider data value
                [self.instantiate(e.data['name'], provider or get_crud_by_name(e.data['provider']))
                 for e in page_entities
                 if e.data.get('provider') != '']  # safe provider check, archived shows no provider
            )

        # filtering
        if self.filters.get("names"):
            names = self.filters["names"]
            entities = [e for e in entities if e.name in names]
        if self.filters.get("name"):
            name = self.filters["name"]
            entities = [e for e in entities if e.name == name]

        return entities


@navigator.register(InstanceCollection, 'All')
class All(CFMENavigateStep):
    VIEW = InstanceAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Instances')
        self.view.sidebar.instances.tree.click_path('All Instances')

    def resetter(self, *args, **kwargs):
        # If a filter was applied, it will persist through navigation and needs to be cleared
        self.view.entities.search.remove_search_filters()
        self.view.toolbar.reload.click()


@navigator.register(InstanceCollection, 'AllForProvider')
@navigator.register(Instance, 'AllForProvider')
class AllForProvider(CFMENavigateStep):
    VIEW = InstanceProviderAllView

    def prerequisite(self):
        try:
            view = navigate_to(self.obj, 'All')
        except NavigationDestinationNotFound:
            view = navigate_to(self.obj.parent, 'All')
        finally:
            return view

    def step(self, *args, **kwargs):
        if isinstance(self.obj, InstanceCollection) and self.obj.filters.get('provider'):
            # the collection is navigation target, use its filter value
            provider_name = self.obj.filters['provider'].name
        elif isinstance(self.obj, Instance):
            provider_name = self.obj.provider.name
        else:
            raise DestinationNotFound("Unable to identify a provider for AllForProvider navigation")

        self.view.sidebar.instances_by_provider.tree.click_path('Instances by Provider',
                                                                provider_name)

    def resetter(self, *args, **kwargs):
        # If a filter was applied, it will persist through navigation and needs to be cleared
        if self.view.adv_search_clear.is_displayed:
            logger.debug('Clearing advanced search filter')
            self.view.adv_search_clear.click()
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'Details')
class Details(CFMENavigateStep):
    VIEW = InstanceDetailsView

    def prerequisite(self, *args, **kwargs):
        return navigate_to(self.obj.parent,
                           'AllForProvider' if self.obj.parent.filters.get('provider')
                           else 'All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True,
                                                             use_search=True)
        except ItemNotFound:
            raise ItemNotFound('Failed to locate instance with name "{}"'.format(self.obj.name))
        row.click()

    def resetter(self, *args, **kwargs):
        self.view.toolbar.reload.click()


@navigator.register(Instance, 'ArchiveDetails')
class ArchiveDetails(CFMENavigateStep):
    VIEW = InstanceDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True,
                                                             use_search=True)
        except ItemNotFound:
            raise ItemNotFound('Failed to locate instance with name "{}"'.format(self.obj.name))
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


@navigator.register(InstanceCollection, 'Provision')
class Provision(CFMENavigateStep):
    VIEW = ProvisionView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Provision Instances')


@navigator.register(Instance, "PolicySimulation")
class PolicySimulation(CFMENavigateStep):
    VIEW = PolicySimulationView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select("Policy Simulation")


@navigator.register(InstanceCollection, "PolicySimulation")  # noqa
class PolicySimulationOnCollection(CFMENavigateStep):
    VIEW = PolicySimulationView

    def prerequisite(self):
        provider = self.obj.filters.get("provider")
        if provider:
            return navigate_to(provider, "Instances")
        else:
            return navigate_to(self.obj, "All")

    def step(self, *args, **kwargs):
        # click the checkbox of every object in the filtered collection
        for entity in self.obj.all():
            self.prerequisite_view.entities.get_entity(name=entity.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select("Policy Simulation")


@navigator.register(Instance, 'SetOwnership')
class SetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    # No am_i_here because the page only indicates name and not provider
    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(Instance, 'SetRetirement')
class SetRetirement(CFMENavigateStep):
    VIEW = RetirementViewWithOffset
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
    def VIEW(self):     # noqa
        return self.obj.provider.vm_utilization_view

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
