# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View, Select
from widgetastic_manageiq import (
    Accordion, BaseEntitiesView, BootstrapSelect, BreadCrumb, ItemsToolBarViewSelector,
    ManageIQTree, SummaryTable, Text, TextInput)
from widgetastic_patternfly import Dropdown, Button

from cfme.base.ui import BaseLoggedInPage
from cfme.common import CustomButtonEventsMixin
from cfme.exceptions import ItemNotFound, SecurityGroupsNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for


class SecurityGroupToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class SecurityGroupDetailsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class SecurityGroupDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class SecurityGroupDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    firewall_rules = SummaryTable(title="Firewall Rules")


class SecurityGroupAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class SecurityGroupAddForm(View):
    network_manager = BootstrapSelect(id='ems_id')
    name = TextInput(name='name')
    description = TextInput(name='description')
    cloud_tenant = Select(name='cloud_tenant_id')
    add = Button('Add')
    cancel = Button('Cancel')


class SecurityGroupView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_security_groups(self):
        return(
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Networks', 'Security Groups'])


class SecurityGroupAllView(SecurityGroupView):
    @property
    def is_displayed(self):
        return (
            self.in_security_groups and
            self.entities.title.text == 'Security Groups')

    toolbar = View.nested(SecurityGroupToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)


class SecurityGroupDetailsView(SecurityGroupView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_security_groups and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(SecurityGroupDetailsToolbar)
    sidebar = View.nested(SecurityGroupDetailsAccordion)
    entities = View.nested(SecurityGroupDetailsEntities)


class SecurityGroupAddView(SecurityGroupView):
    @property
    def is_displayed(self):
        return (
            self.in_security_groups and
            self.entities.breadcrumb.active_location == 'Add New Security Group' and
            self.entities.title.text == 'Add New Security Group')

    entities = View.nested(SecurityGroupAddEntities)
    form = View.nested(SecurityGroupAddForm)


@attr.s
class SecurityGroup(BaseEntity, CustomButtonEventsMixin):
    """ Automate Model page of SecurityGroup

    Args:
        provider (obj): Provider name for Network Manager
        name(str): name of the Security Group
        description (str): Security Group description
    """
    _param_name = "SecurityGroup"

    name = attr.ib()
    provider = attr.ib()
    description = attr.ib(default="")

    def refresh(self):
        self.provider.refresh_provider_relationships()
        self.browser.refresh()

    def delete(self, cancel=False, wait=False):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Delete this Security Group',
                                               handle_alert=(not cancel))
        # cancel doesn't redirect, confirmation does
        view.flush_widget_cache()
        if not cancel:
            view = self.create_view(SecurityGroupAllView)
            view.is_displayed
            view.flash.assert_success_message('Delete initiated for 1 Security Group.')

        if wait:
            wait_for(
                lambda: self.name in view.entities.all_entity_names,
                message="Wait Security Group to disappear",
                fail_condition=True,
                num_sec=500,
                timeout=1000,
                delay=20,
                fail_func=self.refresh
            )

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except SecurityGroupsNotFound:
            return False
        else:
            return True


@attr.s
class SecurityGroupCollection(BaseCollection):
    """ Collection object for the :py:class: `cfme.cloud.SecurityGroup`. """
    ENTITY = SecurityGroup

    def create(self, name, description, provider, cancel=False, wait=False):
        """Create new Security Group.

        Args:
            provider (obj): Provider name for Network Manager
            name (str): name of the Security Group
            description (str): Security Group description
            cancel (boolean): Cancel Security Group creation
            wait (boolean): wait if Security Group created
        """

        view = navigate_to(self, 'Add')
        changed = view.form.fill({'network_manager': "{} Network Manager".format(provider.name),
                                  'name': name,
                                  'description': description,
                                  'cloud_tenant': 'admin'})

        if cancel and changed:
            view.form.cancel.click()
            flash_message = 'Add of new Security Group was cancelled by the user'
        else:
            view.form.add.click()
            flash_message = 'Security Group "{}" created'.format(name)

        # add/cancel should redirect, new view
        view = self.create_view(SecurityGroupAllView)
        view.flash.assert_success_message(flash_message)
        view.entities.paginator.set_items_per_page(500)

        sec_groups = self.instantiate(name, provider, description)
        if wait:
            wait_for(
                lambda: sec_groups.name in view.entities.all_entity_names,
                message="Wait Security Group to appear",
                num_sec=400,
                timeout=1000,
                delay=20,
                fail_func=sec_groups.refresh,
                handle_exception=True
            )

        return sec_groups
    # TODO: Delete collection as Delete option is not available on List view and update


@navigator.register(SecurityGroupCollection, 'All')
class SecurityGroupAll(CFMENavigateStep):
    VIEW = SecurityGroupAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    VIEW = SecurityGroupDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
        except ItemNotFound:
            raise SecurityGroupsNotFound("Security Groups {} not found".format(
                self.obj.name))


@navigator.register(SecurityGroupCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = SecurityGroupAddView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        """Raises DropdownItemDisabled from widgetastic_patternfly
        if no RHOS Network manager present"""
        # Todo remove when fixed 1520669
        if (BZ(1520669, forced_streams='5.9').blocks and
                self.prerequisite_view.flash.messages):
            self.prerequisite_view.flash.dismiss()
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Security Group')
