import attr
from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.networks.views import SecurityGroupDetailsView, SecurityGroupView, SecurityGroupAddView
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.wait import wait_for


@attr.s
class SecurityGroup(BaseEntity, Taggable):
    """ Automate Model page of SecurityGroup

    Args:
        provider (obj): Provider name for Network Manager
        name(str): name of the Security Group
        description (str): Security Group description
    """
    _param_name = "SecurityGroup"

    name = attr.ib()
    provider = attr.ib()
    description = attr.ib(default=None)

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
            view = self.create_view(SecurityGroupView)
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
        except ItemNotFound:
            return False
        else:
            return True


@attr.s
class SecurityGroupCollection(BaseCollection):
    """Collection object for the :py:class: `cfme.cloud.SecurityGroup`. """
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
        view = self.create_view(SecurityGroupView)
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

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'SecurityGroups')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=s.name) for s in list_networks_obj]


@navigator.register(SecurityGroupCollection, 'All')
class All(CFMENavigateStep):
    VIEW = SecurityGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Security Groups')

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(SecurityGroup, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = SecurityGroupDetailsView

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(SecurityGroupCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = SecurityGroupAddView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        """Raises DropdownItemDisabled from widgetastic_patternfly
        if no RHOS Network manager present"""
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Security Group')
