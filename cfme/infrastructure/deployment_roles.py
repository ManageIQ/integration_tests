""" A model of an Infrastructure Deployment roles in CFME"""
import attr

from functools import partial

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import ParametrizedView, View
from widgetastic_manageiq import (Accordion,
                                  BaseEntitiesView,
                                  BaseListEntity,
                                  BaseQuadIconEntity,
                                  BaseTileIconEntity,
                                  BootstrapSelect,
                                  BootstrapTreeview,
                                  BreadCrumb,
                                  CompareToolBarActionsView,
                                  ItemsToolBarViewSelector,
                                  JSBaseEntity,
                                  NonJSBaseEntity,
                                  SummaryTable,
                                  Table,
                                  Text
                                  )
from widgetastic_patternfly import (BootstrapNav,
                                    Button,
                                    Dropdown,
                                    FlashMessages
                                    )

from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import ItemNotFound, RoleNotFound
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.modeling.base import BaseCollection, BaseEntity


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
    download = Button(title='Download summary in PDF format')


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


class DepRoleQuadIconEntity(BaseQuadIconEntity):
    @property
    def data(self):
        return self.browser.get_attribute("alt", self.QUADRANT.format(pos="a"))


class DepRoleTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(DepRoleQuadIconEntity)


class DepRoleListEntity(BaseListEntity):
    pass


class NonJSDepRoleEntity(NonJSBaseEntity):
    quad_entity = DepRoleQuadIconEntity
    list_entity = DepRoleListEntity
    tile_entity = DepRoleTileIconEntity


def DeploymentRoleEntity():  # noqa
    """Temporary wrapper for Deployment Role Entity during transition to JS based Entity """
    return VersionPick({
        Version.lowest(): NonJSDepRoleEntity,
        '5.9': JSBaseEntity,
    })


class DeploymentRoleEntitiesView(BaseEntitiesView):
    """The entities on the main list Deployment Role page"""

    @property
    def entity_class(self):
        return DeploymentRoleEntity().pick(self.browser.product_version)


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
    flash = FlashMessages(
        './/div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
        'contains(@class, "flash_text_div")]')

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
    including_entities = View.include(DeploymentRoleEntitiesView, use_parent=True)

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
    including_entities = View.include(DeploymentRoleEntitiesView, use_parent=True)

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
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_dep_role and
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


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


class DeploymentRoleManagePoliciesView(DeploymentRoleView):
    """Deployment role Manage Policies view."""
    breadcrumb = BreadCrumb()
    policies = BootstrapTreeview("protectbox")
    save_button = Button("Save")
    reset_button = Button("Reset")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        """Is this page currently displayed"""
        return (
            self.in_dep_role and
            (self.breadcrumb.active_location == "'Cluster / Deployment Role' Policy Assignment" or
             self.breadcrumb.active_location == "'Deployment Role' Policy Assignment")
        )


@attr.s
class DeploymentRoles(BaseEntity):
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
        view.toolbar.configuration.item_select('Remove item',
                                               handle_alert=not cancel)

        if not cancel:
            view = self.create_view(DeploymentRoleAllView)
            assert view.is_displayed
            view.flash.assert_success_message("The selected Clusters / "
                                              "Deployment Roles was deleted")


@attr.s
class DeploymentRoleCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.infrastructure.deployment_role.DeploymentRoles'"""
    ENTITY = DeploymentRoles

    # TODO - Once the OpenStack provider is able to give you a deploymentRoleCollection the
    # need for the provider arg here will go as it will become a filter
    def all(self):
        view = navigate_to(self, 'All')
        roles = [self.instantiate(name=item.name)
                 for item in view.entities.get_all()]
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
                    view.entities.get_entity(role.name).check()
                except ItemNotFound:
                    raise RoleNotFound("Deployment role {} not found".format(role.name))

            view.toolbar.configuration.item_select('Remove selected items',
                                                   handle_alert=True)

            assert view.is_displayed
            flash_msg = ("Delete initiated for {} Clusters / Deployment Roles from the CFME "
                         "Database".format(len(roles)))
            view.flash.assert_success_message(flash_msg)
        else:
            raise RoleNotFound('No Deployment Role for Deletion')


@navigator.register(DeploymentRoleCollection, 'All')
class All(CFMENavigateStep):
    VIEW = DeploymentRoleAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
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
            self.prerequisite_view.entities.get_entity(by_name=self.obj.name,
                                                       surf_pages=True).click()
        except ItemNotFound:
            raise RoleNotFound("Deployment Role {} not found".format(self.obj.name))


@navigator.register(DeploymentRoles, 'AllForProvider')
class AllForProvider(CFMENavigateStep):
    VIEW = DeploymentRoleAllForProviderView
    prerequisite = NavigateToAttribute('provider', 'Details')

    def step(self):
        try:
            self.prerequisite_view.entities.relationships.click_at('Deployment Roles')
        except NameError:
            self.prerequisite_view.entities.relationships.click_at('Clusters / Deployment Roles')


@navigator.register(DeploymentRoles, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DeploymentRoleDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        try:
            self.prerequisite_view.entities.get_entity(by_name=self.obj.name).click()
        except ItemNotFound:
            raise RoleNotFound("Deployment Role {} not found".format(self.obj.name))
