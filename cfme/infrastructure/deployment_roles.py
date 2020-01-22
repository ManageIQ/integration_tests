""" A model of an Infrastructure Deployment roles in CFME"""
from functools import partial

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.common import PolicyProfileAssignable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BootstrapSelect
from widgetastic_manageiq import CompareToolBarActionsView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table


class DeploymentRoleToolbar(View):
    """The toolbar on the Deployment Role page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class DeploymentRoleDetailsToolbar(View):
    """The toolbar on the Deployment Role details page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button(title='Print or export summary')


class DeploymentRoleComparisonToolbar(View):
    """The toolbar on Comparison Page of roles"""
    actions = View.nested(CompareToolBarActionsView)
    download = Dropdown('Download')


class DeploymentRoleDetailsAccordion(View):
    """The accordion on the Deployment Role details page"""

    @View.nested
    class properties(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="ems_prop"]//ul')

    @View.nested
    class relationships(Accordion):  # noqa
        nav = BootstrapNav('//div[@id="ems_rel"]//ul')


class DeploymentRoleDetailsEntities(View):
    """The entities on the Deployment Role details page"""
    breadcrumb = BreadCrumb()
    relationships = SummaryTable(title='Relationships')
    total_for_node = SummaryTable(title='Totals for Nodes')
    total_for_vm = SummaryTable(title='Totals for VMs')
    smart_management = SummaryTable(title='Smart Management')


class DeploymentRoleComparisonEntities(View):
    """The entities on compare Deployment role page"""
    breadcrumb = BreadCrumb()
    table = Table('//*[@id="compare-grid"]/table')


class DeploymentRoleView(BaseLoggedInPage):
    """A base view for all the Deployment Role pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_dep_role(self):
        """Determine if the Deployment page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                   'Deployment Roles'])


class DeploymentRoleAllView(DeploymentRoleView):
    """The all Deployment Role page"""
    toolbar = View.nested(DeploymentRoleToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        """This is page currently being displayed"""
        return (
            self.in_dep_role and
            (self.title.text == 'Deployment Roles' or
             self.title.text == 'All Cluster / Deployment Role'))


class DeploymentRoleAllForProviderView(DeploymentRoleView):
    """The Deployment Role for Provider page"""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(DeploymentRoleToolbar)
    sidebar = View.nested(DeploymentRoleDetailsAccordion)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (All Deployment Roles)'.format(self.context['object'].provider.name)

        return (
            self.logged_in_as_current_user and
            self.breadcrumb.active_location == expected_title)


class DeploymentRoleDetailsView(DeploymentRoleView):
    """The details page for a Deployment Roles"""
    toolbar = View.nested(DeploymentRoleDetailsToolbar)
    sidebar = View.nested(DeploymentRoleDetailsAccordion)
    entities = View.nested(DeploymentRoleDetailsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        obj = self.context['object']
        return (
            self.in_dep_role and
            self.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb
        )


class DeploymentRoleComparisonView(DeploymentRoleView):
    """The page for comparison of Deployment Role"""
    toolbar = View.nested(DeploymentRoleComparisonToolbar)
    entities = View.nested(DeploymentRoleComparisonEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = 'Compare Cluster / Deployment Role'
        return (
            self.in_dep_role and
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class DeploymentRoleEditTagsView(DeploymentRoleView):
    """The edit tags of Deployment Role"""
    breadcrumb = BreadCrumb()
    title = Text('#explorer_title_text')
    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_dep_role and
            self.breadcrumb.active_location == 'Tag Assignment')


@attr.s
class DeploymentRoles(BaseEntity, PolicyProfileAssignable):
    """ Model of an infrastructure deployment roles in cfme

    Args:
        name: Name of the role.
        provider: provider this role is attached to
            (deployment roles available only for Openstack!).
    """
    # TODO: add deployment role creation method with cli
    name = attr.ib()

    # TODO : Replace this with a walk when the provider can give us clusters
    @property
    def provider(self):
        # return parent_of_type(self, OpenstackInfraProvider)  <--- should be this
        return self.parent.filters.get('provider')

    def delete(self, cancel=False):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove item from Inventory',
                                               handle_alert=not cancel)

        if not cancel:
            view = self.create_view(DeploymentRoleAllView, wait=5)
            view.flash.assert_success_message(
                "The selected Clusters / Deployment Roles was deleted"
            )


@attr.s
class DeploymentRoleCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.infrastructure.deployment_role.DeploymentRoles'"""
    ENTITY = DeploymentRoles

    # TODO - Once the OpenStack provider is able to give you a deploymentRoleCollection the
    # need for the provider arg here will go as it will become a filter
    def all(self):
        view = navigate_to(self, 'All')
        roles = [self.instantiate(name=item) for item in view.entities.entity_names]
        return roles

    def delete(self, *roles):
        """Delete one or more Deployment Role from list of Deployment Roles

        Args:
            One or Multiple 'cfme.infrastructure.deployment_role.DeploymentRoles' objects
        """

        view = navigate_to(self, 'All')

        if view.entities.get_all(surf_pages=True) and roles:
            for role in roles:
                try:
                    view.entities.get_entity(name=role.name).ensure_checked()
                except ItemNotFound:
                    raise ItemNotFound("Deployment role {} not found".format(role.name))

            view.toolbar.configuration.item_select('Remove selected items',
                                                   handle_alert=True)

            assert view.is_displayed
            flash_msg = ("Delete initiated for {} Clusters / Deployment Roles from the CFME "
                         "Database".format(len(roles)))
            view.flash.assert_success_message(flash_msg)
        else:
            raise ItemNotFound('No Deployment Role for Deletion')


@navigator.register(DeploymentRoleCollection, 'All')
class All(CFMENavigateStep):
    VIEW = DeploymentRoleAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        nav_select = partial(self.prerequisite_view.navigation.select, 'Compute', 'Infrastructure')
        try:
            nav_select('Deployment Roles')
        except NoSuchElementException:
            nav_select('Clusters / Deployment Roles')


@navigator.register(DeploymentRoles, 'Details')
class Details(CFMENavigateStep):
    VIEW = DeploymentRoleDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        """Navigate to the details page of Role"""
        try:
            self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                       surf_pages=True).click()
        except ItemNotFound:
            raise ItemNotFound("Deployment Role {} not found".format(self.obj.name))


@navigator.register(DeploymentRoles, 'AllForProvider')
class AllForProvider(CFMENavigateStep):
    VIEW = DeploymentRoleAllForProviderView
    prerequisite = NavigateToAttribute('provider', 'Details')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.summary('Relationships').click_at('Deployment Roles')
        except NameError:
            (self.prerequisite_view.entities.summary('Relationships').click_at
                ('Clusters / Deployment Roles'))


@navigator.register(DeploymentRoles, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DeploymentRoleDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(name=self.obj.name).click()
        except ItemNotFound:
            raise ItemNotFound("Deployment Role {} not found".format(self.obj.name))
