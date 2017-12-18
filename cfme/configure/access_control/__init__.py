import attr
import importscan
import sentaku
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View, Text
from widgetastic_patternfly import (
    BootstrapSelect, Button, Input, CheckableBootstrapTreeview,
    BootstrapSwitch, CandidateNotFound, Dropdown)

from cfme.base.credential import Credential
from cfme.base.ui import ConfigurationView
from cfme.exceptions import RBACOperationBlocked
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (
    Table, BaseListEntity)


class AccessControlToolbar(View):
    """ Toolbar on the Access Control page """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


@attr.s
class User(Updateable, Pretty, BaseEntity, sentaku.Element):
    """ Class represents an user in CFME UI

    Args:
        name: Name of the user
        credential: User's credentials
        email: User's email
        group: User's group for assigment
    """
    pretty_attrs = ['name', 'group']

    name = attr.ib(default=None)
    credential = attr.ib(default=None)
    email = attr.ib(default=None)
    group = attr.ib(default=None)
    _restore_user = attr.ib(default=None, init=False)

    change_stored_password = sentaku.ContextualMethod()
    copy = sentaku.ContextualMethod()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    edit_tags = sentaku.ContextualMethod()
    remove_tag = sentaku.ContextualMethod()
    get_tags = sentaku.ContextualMethod()

    def __enter__(self):
        if self._restore_user != self.appliance.user:
            logger.info('Switching to new user: %s', self.credential.principal)
            self._restore_user = self.appliance.user
            self.appliance.server.logout()
            self.appliance.user = self

    def __exit__(self, *args, **kwargs):
        if self._restore_user != self.appliance.user:
            logger.info('Restoring to old user: %s', self._restore_user.credential.principal)
            self.appliance.server.logout()
            self.appliance.user = self._restore_user
            self._restore_user = None

    @property
    def exists(self):
        users = self.appliance.rest_api.collections.users.find_by(userid=self.credential.principal)
        if users:
            return True
        else:
            return False

    @property
    def description(self):
        return self.credential.principal


@attr.s
class UserCollection(BaseCollection, sentaku.Element):

    ENTITY = User

    create = sentaku.ContextualMethod()

    def simple_user(self, userid, password):
        creds = Credential(principal=userid, secret=password)
        return self.instantiate(name=userid, credential=creds)


@attr.s
class Group(BaseEntity, sentaku.Element):
    """Represents a group in CFME UI

    Properties:
        description: group description
        role: group role
        tenant: group tenant
        user_to_lookup: ldap user to lookup
        ldap_credentials: ldap user credentials
        tag: tag for group restriction
        host_cluster: host/cluster for group restriction
        vm_template: vm/template for group restriction
    """
    pretty_attrs = ['description', 'role']

    description = attr.ib(default=None)
    role = attr.ib(default=None)
    tenant = attr.ib(default="My Company")
    ldap_credentials = attr.ib(default=None)
    user_to_lookup = attr.ib(default=None)
    tag = attr.ib(default=None)
    host_cluster = attr.ib(default=None)
    vm_template = attr.ib(default=None)

    add_group_from_ldap_lookup = sentaku.ContextualMethod()
    add_group_from_ext_auth_lookup = sentaku.ContextualMethod()
    update = sentaku.ContextualMethod()
    delete = sentaku.ContextualMethod()
    edit_tags = sentaku.ContextualMethod()
    remove_tag = sentaku.ContextualMethod()
    get_tags = sentaku.ContextualMethod()
    set_group_order = sentaku.ContextualMethod()

    def _retrieve_ldap_user_groups(self):
        """ Retrive ldap user groups
            return: AddGroupView
        """
        view = navigate_to(self.parent, 'Add')
        view.fill({'lookup_ldap_groups_chk': True,
                   'user_to_look_up': self.user_to_lookup,
                   'username': self.ldap_credentials.principal,
                   'password': self.ldap_credentials.secret})
        view.retrieve_button.click()
        return view

    def _retrieve_ext_auth_user_groups(self):
        """ Retrive external authorization user groups
            return: AddGroupView
        """
        view = navigate_to(self.parent, 'Add')
        view.fill({'lookup_ldap_groups_chk': True,
                   'user_to_look_up': self.user_to_lookup})
        view.retrieve_button.click()
        return view

    def _fill_ldap_group_lookup(self, view):
        """ Fills ldap info for group lookup

        Args: view: view for group creation(AddGroupView)
        """
        view.fill({'ldap_groups_for_user': self.description,
                   'description_txt': self.description,
                   'role_select': self.role,
                   'group_tenant': self.tenant})
        view.add_button.click()
        view = self.create_view(AllGroupView)
        view.flash.assert_success_message('Group "{}" was saved'.format(self.description))
        assert view.is_displayed

    def _set_group_restriction(self, tab_view, item, update=False):
        """ Sets tag/host/template restriction for the group

        Args:
            tab_view: tab view
            item: path to check box that should be selected/deselected
            update: If True - checkbox state will be updated

        Returns: True - if update is successful
        """
        updated_result = False
        if item is not None:
            if update:
                if tab_view.tree.node_checked(*item):
                    tab_view.tree.uncheck_node(*item)
                else:
                    tab_view.tree.check_node(*item)
                updated_result = True
            else:
                tab_view.tree.fill(item)
        return updated_result

    @property
    def group_order(self):
        view = navigate_to(self, 'EditGroupSequence')
        return view.group_order_selector.items

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False


@attr.s
class GroupCollection(BaseCollection, sentaku.Element):
    """ Collection object for the :py:class: `cfme.configure.access_control.Group`. """
    ENTITY = Group

    create = sentaku.ContextualMethod()


####################################################################################################
# RBAC ROLE METHODS
####################################################################################################
class RoleForm(ConfigurationView):
    """ Role Form for CFME UI """
    name_txt = Input(name='name')
    vm_restriction_select = BootstrapSelect(id='vm_restriction')
    product_features_tree = CheckableBootstrapTreeview("features_treebox")

    cancel_button = Button('Cancel')


class AddRoleView(RoleForm):
    """ Add Role View """
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Adding a new Role'
        )


class EditRoleView(RoleForm):
    """ Edit Role View """
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Editing Role "{}"'.format(self.context['object'].name)
        )


class DetailsRoleView(RoleForm):
    """ Details Role View """
    toolbar = View.nested(AccessControlToolbar)

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Role "{}"'.format(self.context['object'].name) and
            # tree.currently_selected returns a list of strings with each item being the text of
            # each level of the accordion. Last element should be the Role's name
            self.accordions.accesscontrol.tree.currently_selected[-1] == self.context['object'].name
        )


class AllRolesView(ConfigurationView):
    """ All Roles View """
    toolbar = View.nested(AccessControlToolbar)
    table = Table("//div[@id='main_div']//table")

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Access Control Roles'
        )


@attr.s
class Role(Updateable, Pretty, BaseEntity):
    """ Represents a role in CFME UI

    Args:
        name: role name
        vm_restriction: restriction used for role
        product_features: product feature to select
        appliance: appliance unter test
    """

    pretty_attrs = ['name', 'product_features']

    name = attr.ib(default=None)
    vm_restriction = attr.ib(default=None)
    product_features = attr.ib(default=None)

    def __attrs_post_init__(self):
        if not self.product_features:
            self.product_features = []

    def update(self, updates):
        """ Update role method

        Args:
            updates: role data that should be changed

        Note: In case updates is the same as original role data, update will be canceled,
              as 'Save' button will not be active
        """
        flash_blocked_msg = "Read Only Role \"{}\" can not be edited".format(self.name)
        edit_role_txt = 'Edit this Role'
        view = navigate_to(self, 'Details')
        if not view.toolbar.configuration.item_enabled(edit_role_txt):
            raise RBACOperationBlocked("Configuration action '{}' is not enabled".format(
                edit_role_txt))

        view = navigate_to(self, 'Edit')
        try:
            view.flash.assert_message(flash_blocked_msg)
            raise RBACOperationBlocked(flash_blocked_msg)
        except AssertionError:
            pass

        changed = view.fill({
            'name_txt': updates.get('name'),
            'vm_restriction_select': updates.get('vm_restriction')
        })
        feature_changed = self.set_role_product_features(view, updates.get('product_features'))
        if changed or feature_changed:
            view.save_button.click()
            flash_message = 'Role "{}" was saved'.format(updates.get('name', self.name))
        else:
            view.cancel_button.click()
            flash_message = 'Edit of Role was cancelled by the user'
        view = self.create_view(DetailsRoleView, override=updates)
        view.flash.assert_message(flash_message)
        assert view.is_displayed

    def delete(self, cancel=True):
        """ Delete existing role

        Args:
            cancel: Default value 'True', role will be deleted
                    'False' - deletion of role will be canceled
        Throws:
            RBACOperationBlocked: If operation is blocked due to current user
                not having appropriate permissions OR delete is not allowed
                for currently selected role
        """
        flash_blocked_msg = ("Role \"{}\": Error during delete: Cannot delete record "
                             "because of dependent entitlements".format(self.name))
        flash_success_msg = 'Role "{}": Delete successful'.format(self.name)
        delete_role_txt = 'Delete this Role'

        view = navigate_to(self, 'Details')

        if not view.toolbar.configuration.item_enabled(delete_role_txt):
            raise RBACOperationBlocked("Configuration action '{}' is not enabled".format(
                delete_role_txt))

        view.toolbar.configuration.item_select(delete_role_txt, handle_alert=cancel)
        try:
            view.flash.assert_message(flash_blocked_msg)
            raise RBACOperationBlocked(flash_blocked_msg)
        except AssertionError:
            pass

        view.flash.assert_message(flash_success_msg)

        if cancel:
            view = self.create_view(AllRolesView)
            view.flash.assert_success_message(flash_success_msg)
        else:
            view = self.create_view(DetailsRoleView)
        assert view.is_displayed

    def copy(self, name=None):
        """ Creates copy of existing role

        Returns: Role object of copied role
        """
        if name is None:
            name = "{}_copy".format(self.name)
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Copy this Role to a new Role')
        view = self.create_view(AddRoleView)
        new_role = self.parent.instantiate(name=name)
        view.fill({'name_txt': new_role.name})
        view.add_button.click()
        view = self.create_view(AllRolesView)
        view.flash.assert_success_message('Role "{}" was saved'.format(new_role.name))
        assert view.is_displayed
        return new_role

    def set_role_product_features(self, view, product_features):
        """ Sets product features for role restriction

        Args:
            view: AddRoleView or EditRoleView
            product_features: list of product features with options to select
        """
        feature_update = False
        if product_features is not None and isinstance(product_features, (list, tuple, set)):
            for path, option in product_features:
                if option:
                    view.product_features_tree.check_node(*path)
                else:
                    view.product_features_tree.uncheck_node(*path)
            feature_update = True
        return feature_update


@attr.s
class RoleCollection(BaseCollection):
    ENTITY = Role

    def create(self, name=None, vm_restriction=None, product_features=None, cancel=False):
        """ Create role method
        Args:
            cancel: True - if you want to cancel role creation,
                    by default, role will be created
        Raises:
            RBACOperationBlocked: If operation is blocked due to current user
                not having appropriate permissions OR update is not allowed
                for currently selected role
        """
        flash_blocked_msg = "Name has already been taken"

        role = self.instantiate(
            name=name, vm_restriction=vm_restriction, product_features=product_features
        )

        view = navigate_to(self, 'Add')
        view.fill({'name_txt': role.name,
                   'vm_restriction_select': role.vm_restriction})
        role.set_role_product_features(view, role.product_features)
        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Role was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Role "{}" was saved'.format(role.name)
        view = self.create_view(AllRolesView)

        try:
            view.flash.assert_message(flash_blocked_msg)
            raise RBACOperationBlocked(flash_blocked_msg)
        except AssertionError:
            pass

        view.flash.assert_success_message(flash_message)

        assert view.is_displayed

        return role


@navigator.register(RoleCollection, 'All')
class RoleAll(CFMENavigateStep):
    VIEW = AllRolesView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Roles')


@navigator.register(RoleCollection, 'Add')
class RoleAdd(CFMENavigateStep):
    VIEW = AddRoleView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Role")


@navigator.register(Role, 'Details')
class RoleDetails(CFMENavigateStep):
    VIEW = DetailsRoleView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.browser.refresh()  # workaround for 5.9 issue of role now shown
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Roles', self.obj.name)


@navigator.register(Role, 'Edit')
class RoleEdit(CFMENavigateStep):
    VIEW = EditRoleView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Role')


####################################################################################################
# RBAC TENANT METHODS
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
class TenantForm(ConfigurationView):
    """ Tenant Form """
    name = Input(name='name')
    description = Input(name='description')
    add_button = Button('Add')
    cancel_button = Button('Cancel')


class ListEntity(BaseListEntity):
    pass


class TenantQuotaForm(View):
    cpu_cb = BootstrapSwitch(id='cpu_allocated')
    memory_cb = BootstrapSwitch(id='mem_allocated')
    storage_cb = BootstrapSwitch(id='storage_allocated')
    vm_cb = BootstrapSwitch(id='vms_allocated')
    template_cb = BootstrapSwitch(id='templates_allocated')
    cpu_txt = Input(id='id_cpu_allocated')
    memory_txt = Input(id='id_mem_allocated')
    storage_txt = Input(id='id_storage_allocated')
    vm_txt = Input(id='id_vms_allocated')
    template_txt = Input(id='id_templates_allocated')


class TenantQuotaView(ConfigurationView):
    """ Tenant Quota View """
    form = View.nested(TenantQuotaForm)

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.form.template_cb.is_displayed and
            self.title.text == 'Manage quotas for {} "{}"'.format(self.context['object'].obj_type,
                                                                  self.context['object'].name))


class AllTenantView(ConfigurationView):
    """ All Tenants View """
    toolbar = View.nested(AccessControlToolbar)
    table = Table(VersionPick(
        {Version.lowest(): '//*[@id="records_div"]/table',
         '5.9': '//*[@id="miq-gtl-view"]/miq-data-table/div/table'}))

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Access Control Tenants'
        )


class AddTenantView(ConfigurationView):
    """ Add Tenant View """
    form = View.nested(TenantForm)

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.form.description.is_displayed and
            self.title.text in ('Adding a new Project', 'Adding a new Tenant')
        )


class DetailsTenantView(ConfigurationView):
    """ Details Tenant View """
    toolbar = View.nested(AccessControlToolbar)
    name = Text('Name')
    description = Text('Description')
    parent = Text('Parent')
    table = Table('//*[self::fieldset or @id="fieldset"]/table')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == '{} "{}"'.format(self.context['object'].obj_type,
                                                self.context['object'].name)
        )


class ParentDetailsTenantView(DetailsTenantView):
    """ Parent Tenant Details View """

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == '{} "{}"'.format(self.context['object'].parent_tenant.obj_type,
                                                self.context['object'].parent_tenant.name)
        )


class EditTenantView(View):
    """ Edit Tenant View """
    form = View.nested(TenantForm)
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.form.accordions.accesscontrol.is_opened and
            self.form.description.is_displayed and
            self.form.title.text == 'Editing {} "{}"'.format(self.context['object'].obj_type,
                                                             self.context['object'].name)
        )


@attr.s
class Tenant(Updateable, BaseEntity):
    """ Class representing CFME tenants in the UI.
    * Kudos to mfalesni *

    The behaviour is shared with Project, which is the same except it cannot create more nested
    tenants/projects.

    Args:
        name: Name of the tenant
        description: Description of the tenant
        parent_tenant: Parent tenant, can be None, can be passed as string or object
    """
    obj_type = 'Tenant'

    name = attr.ib()
    description = attr.ib(default="")
    parent_tenant = attr.ib(default=None)
    _default = attr.ib(default=False)

    def update(self, updates):
        """ Update tenant/project method

        Args:
            updates: tenant/project data that should be changed

        Note: In case updates is the same as original tenant/project data, update will be canceled,
            as 'Save' button will not be active
        """
        view = navigate_to(self, 'Edit', wait_for_view=True)
        changed = view.form.fill(updates)
        if changed:
            view.save_button.click()
            if self.appliance.version < '5.9':
                flash_message = 'Project "{}" was saved'.format(updates.get('name', self.name))
            else:
                flash_message = '{} "{}" has been successfully saved.'.format(
                    self.obj_type, updates.get('name', self.name))
        else:
            view.cancel_button.click()
            if self.appliance.version < '5.9':
                flash_message = 'Edit of Project "{}" was cancelled by the user'.format(
                    updates.get('name', self.name))
            else:
                flash_message = 'Edit of {} "{}" was canceled by the user.'.format(
                    self.obj_type, updates.get('name', self.name))
        view = self.create_view(DetailsTenantView, override=updates)
        view.flash.assert_message(flash_message)

    def delete(self, cancel=True):
        """ Delete existing role

        Args:
            cancel: Default value 'True', role will be deleted
                    'False' - deletion of role will be canceled
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select(
            'Delete this item', handle_alert=cancel)
        if cancel:
            view = self.create_view(ParentDetailsTenantView)
            view.flash.assert_success_message(
                'Tenant "{}": Delete successful'.format(self.description))
        else:
            view = self.create_view(DetailsRoleView)
        assert view.is_displayed

    def set_quota(self, **kwargs):
        """ Sets tenant quotas """
        view = navigate_to(self, 'ManageQuotas', wait_for_view=True)
        view.form.fill({'cpu_cb': kwargs.get('cpu_cb'),
                        'cpu_txt': kwargs.get('cpu'),
                        'memory_cb': kwargs.get('memory_cb'),
                        'memory_txt': kwargs.get('memory'),
                        'storage_cb': kwargs.get('storage_cb'),
                        'storage_txt': kwargs.get('storage'),
                        'vm_cb': kwargs.get('vm_cb'),
                        'vm_txt': kwargs.get('vm'),
                        'template_cb': kwargs.get('template_cb'),
                        'template_txt': kwargs.get('template')})
        view.save_button.click()
        view = self.create_view(DetailsTenantView)
        view.flash.assert_success_message('Quotas for {} "{}" were saved'.format(
            self.obj_type, self.name))
        assert view.is_displayed

    @property
    def quota(self):
        view = navigate_to(self, 'Details')
        quotas = {
            'cpu': 'Allocated Virtual CPUs',
            'memory': 'Allocated Memory in GB',
            'storage': 'Allocated Storage in GB',
            'num_vms': 'Allocated Number of Virtual Machines',
            'templates': 'Allocated Number of Templates'
        }

        for field in quotas:
            item = view.table.row(name=quotas[field])
            quotas[field] = {
                'total': item.total_quota.text,
                'in_use': item.in_use.text,
                'allocated': item.allocated.text,
                'available': item.available.text
            }

        return quotas

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        else:
            return self.tree_path == other.tree_path

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    @property
    def tree_path(self):
        if self._default:
            return [self.name]
        else:
            return self.parent_tenant.tree_path + [self.name]

    @property
    def parent_path(self):
        return self.parent_tenant.tree_path


@attr.s
class TenantCollection(BaseCollection):
    """Collection class for Tenant"""
    ENTITY = Tenant

    def get_root_tenant(self):
        return self.instantiate(str(self.appliance.rest_api.collections.tenants[0].name),
                                default=True)

    def create(self, name, description, parent):
        if self.appliance.version > '5.9':
            tenant_success_flash_msg = 'Tenant "{}" has been successfully added.'
        else:
            tenant_success_flash_msg = 'Tenant "{}" was saved'

        tenant = self.instantiate(name, description, parent)

        view = navigate_to(tenant.parent_tenant, 'Details')
        view.toolbar.configuration.item_select('Add child Tenant to this Tenant')
        view = self.create_view(AddTenantView)
        wait_for(lambda: view.is_displayed, timeout=5)
        changed = view.form.fill({'name': name,
                                  'description': description})
        if changed:
            view.form.add_button.click()
        else:
            view.form.cancel_button.click()

        view = self.create_view(ParentDetailsTenantView)

        view.flash.assert_success_message(tenant_success_flash_msg.format(name))

        return tenant

    def delete(self, *tenants):

        view = navigate_to(self, 'All')

        for tenant in tenants:
            try:
                view.table.row(name=tenant.name).check()
            except Exception:
                logger.exception('Failed to check element "%s"', tenant.name)
        else:
            view.toolbar.configuration.item_select('Delete selected items', handle_alert=True)


@navigator.register(TenantCollection, 'All')
class TenantAll(CFMENavigateStep):
    VIEW = AllTenantView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Tenants')


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    VIEW = DetailsTenantView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Tenants', *self.obj.tree_path)


@navigator.register(Tenant, 'Edit')
class TenantEdit(CFMENavigateStep):
    VIEW = EditTenantView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this item')


@navigator.register(Tenant, 'ManageQuotas')
class TenantManageQuotas(CFMENavigateStep):
    VIEW = TenantQuotaView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Manage Quotas')


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# END TENANT METHODS
####################################################################################################


####################################################################################################
# RBAC PROJECT METHODS
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
class Project(Tenant):
    """ Class representing CFME projects in the UI.

    Project cannot create more child tenants/projects.

    Args:
        name: Name of the project
        description: Description of the project
        parent_tenant: Parent project, can be None, can be passed as string or object
    """
    obj_type = 'Project'


class ProjectCollection(TenantCollection):
    """Collection class for Projects under Tenants"""

    ENTITY = Project

    def get_root_tenant(self):
        # returning Tenant directly because 'My Company' needs to be treated like Tenant object,
        # to be able to make child tenant/project under it
        return self.appliance.collections.tenants.instantiate(
            name=str(self.appliance.rest_api.collections.tenants[0].name), default=True)

    def create(self, name, description, parent):
        if self.appliance.version > '5.9':
            project_success_flash_msg = 'Project "{}" has been successfully added.'
        else:
            project_success_flash_msg = 'Project "{}" was saved'

        project = self.instantiate(name, description, parent)

        view = navigate_to(project.parent_tenant, 'Details')
        view.toolbar.configuration.item_select('Add Project to this Tenant')

        view = self.create_view(AddTenantView)
        wait_for(lambda: view.is_displayed, timeout=5)
        changed = view.form.fill({'name': name,
                                  'description': description})
        if changed:
            view.form.add_button.click()
        else:
            view.form.cancel_button.click()

        view = self.create_view(ParentDetailsTenantView)
        view.flash.assert_success_message(project_success_flash_msg.format(name))

        return project

# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# END PROJECT METHODS
####################################################################################################


from . import ui, rest  # NOQA last for import cycles
importscan.scan(ui)
importscan.scan(rest)
