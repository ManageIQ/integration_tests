from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import UpDownSelect, SummaryFormItem
from widgetastic_patternfly import (
    BootstrapSelect, Button, Input, Tab, CheckableBootstrapTreeview,
    BootstrapSwitch, CandidateNotFound)
from widgetastic.widget import Text, Checkbox, View

from cfme.base.credential import Credential
import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import OptionNotAvailable
from cfme.web_ui import Table
from cfme.web_ui.form_buttons import change_stored_password
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.log import logger
from utils.pretty import Pretty
from utils.update import Updateable

from . import ConfigurationView


tag_table = Table("//div[@id='assignments_div']//table")


def simple_user(userid, password):
    creds = Credential(principal=userid, secret=password)
    return User(name=userid, credential=creds)


class UserForm(ConfigurationView):
    title = Text('#explorer_title_text')

    name_txt = Input(name='name')
    userid_txt = Input(name='userid')
    password_txt = Input(id='password')
    password_verify_txt = Input(id='verify')
    email_txt = Input(name='email')
    user_group_select = BootstrapSelect(id='chosen_group')

    cancel_button = Button('Cancel')


class AllUserView(ConfigurationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Access Control EVM Users'
        )


class AddUserView(UserForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == "Adding a new User"
        )


class DetailsUserView(ConfigurationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.title.text == 'EVM User "{}"'.format(self.obj.name) and
            self.access_control.is_opened
        )


class EditUserView(UserForm):
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Editing User "{}"'.format(self.obj.name) and
            self.access_control.is_opened
        )


class EditTagsUserView(ConfigurationView):
    title = Text('#explorer_title_text')

# TODO remove comment, when widget is done
# tag_table = Table("//div[@id='assignments_div']//table")

    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')

    save_button = Button('Save')
    cancel_button = Button('Cancel')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Editing My Company Tags for "EVM Users"'
        )


class User(Updateable, Pretty, Navigatable):
    pretty_attrs = ['name', 'group']

    def __init__(self, name=None, credential=None, email=None, group=None, cost_center=None,
                 value_assign=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.credential = credential
        self.email = email
        self.group = group
        self.cost_center = cost_center
        self.value_assign = value_assign
        self._restore_user = None

    def __enter__(self):
        if self._restore_user != self.appliance.user:
            from cfme.login import logout
            logger.info('Switching to new user: %s', self.credential.principal)
            self._restore_user = self.appliance.user
            logout()
            self.appliance.user = self

    def __exit__(self, *args, **kwargs):
        if self._restore_user != self.appliance.user:
            from cfme.login import logout
            logger.info('Restoring to old user: %s', self._restore_user.credential.principal)
            logout()
            self.appliance.user = self._restore_user
            self._restore_user = None

    def create(self):
        view = navigate_to(self, 'Add')
        view.fill({'name_txt': self.name,
                   'userid_txt': self.credential.principal,
                   'password_txt': self.credential.secret,
                   'password_verify_txt': self.credential.verify_secret,
                   'email_txt': self.email,
                   'user_group_select': getattr(self.group, 'description', None)})
        view.add_button.click()
        view = self.create_view(AllUserView)
        view.flash.assert_success_message('User "{}" was saved'.format(self.name))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        change_stored_password()
        new_updates = {}
        if 'credential' in updates:
            new_updates.update({
                'userid_txt': updates.get('credential').principal,
                'password_txt': updates.get('credential').secret,
                'password_verify_txt': updates.get('credential').verify_secret
            })
        new_updates.update({
            'name_txt': updates.get('name'),
            'email_txt': updates.get('email'),
            'user_group_select': getattr(
                updates.get('group'),
                'description', None)
        })
        view.fill({'name_txt': new_updates.get('name_txt'),
                   'userid_txt': new_updates.get('userid_txt'),
                   'password_txt': new_updates.get('password_txt'),
                   'password_verify_txt': new_updates.get('password_verify_txt'),
                   'email_txt': new_updates.get('email_txt'),
                   'user_group_select': new_updates.get('user_group_select')})
        view.save_button.click()
        view = self.create_view(DetailsUserView)
        view.flash.assert_success_message(
            'User "{}" was saved'.format(updates.get('name', self.name)))

    def copy(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Copy this User to a new User')
        view = self.create_view(AddUserView)
        new_user = User(name="{}copy".format(self.name),
                        credential=Credential(principal='redhat', secret='redhat'))
        change_stored_password()
        view.fill({'name_txt': new_user.name,
                   'userid_txt': new_user.credential.principal,
                   'password_txt': new_user.credential.secret,
                   'password_verify_txt': new_user.credential.verify_secret})
        view.add_button.click()
        view = self.create_view(AllUserView)
        view.flash.assert_success_message('User "{}" was saved'.format(new_user.name))
        return new_user

    def delete(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this User', handle_alert=True)
        view = self.create_view(AllUserView)
        view.flash.assert_success_message('EVM User "{}": Delete successful'.format(self.name))

    def edit_tags(self, tag, value):
        view = navigate_to(self, 'EditTags')
        view.fill({'select_tag': tag,
                   'select_value': value})
        view.save_button.click()
        view = self.create_view(DetailsUserView)
        view.flash.assert_success_message('Tag edits were successfully saved')

    def remove_tag(self, tag, value):
        view = navigate_to(self, 'EditTags')
        row = tag_table.find_row_by_cells({'category': tag, 'assigned_value': value},
                                          partial_check=True)
        sel.click(row[0])
        view.save_button.click()
        view = self.create_view(DetailsUserView)
        view.flash.assert_success_message('Tag edits were successfully saved')

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    @property
    def description(self):
        return self.credential.principal


@navigator.register(User, 'All')
class UserAll(CFMENavigateStep):
    VIEW = AllUserView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.view.settings.select_item('Configuration')
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Users')


@navigator.register(User, 'Add')
class UserAdd(CFMENavigateStep):
    VIEW = AddUserView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a new User")


@navigator.register(User, 'Details')
class UserDetails(CFMENavigateStep):
    VIEW = DetailsUserView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Users', self.obj.name)


@navigator.register(User, 'Edit')
class UserEdit(CFMENavigateStep):
    VIEW = EditUserView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Edit this User')


@navigator.register(User, 'EditTags')
class UserTagsEdit(CFMENavigateStep):
    VIEW = EditTagsUserView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.policy.item_select("Edit 'My Company' Tags for this User")


class GroupForm(ConfigurationView):
    title = Text('#explorer_title_text')

    ldap_groups_for_user = BootstrapSelect(id='ldap_groups_user')
    description_txt = Input(name='description')
    lookup_ldap_groups_chk = Checkbox(name='lookup')
    role_select = BootstrapSelect(id='group_role')
    group_tenant = BootstrapSelect(id='group_tenant')
    user_to_look_up = Input(name='user')
    username = Input(name='user_id')
    password = Input(name='password')

    tag = SummaryFormItem('Smart Management', 'My Company Tags')

    cancel_button = Button('Cancel')
    retrieve_button = Button('Retrieve')

    @View.nested
    class my_company_tags(Tab):     # noqa
        TAB_NAME = "My Company Tags"
        tag_tree = CheckableBootstrapTreeview('tags_treebox')

    @View.nested
    class hosts_and_clusters(Tab):      # noqa
        TAB_NAME = "Hosts & Clusters"
        hosts_clusters_tree = CheckableBootstrapTreeview('hac_treebox')

    @View.nested
    class vms_and_templates(Tab):       # noqa
        TAB_NAME = "VMs & Templates"
        vms_templates_tree = CheckableBootstrapTreeview('vat_treebox')


class AddGroupView(GroupForm):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == "Adding a new Group"
        )


class DetailsGroupView(ConfigurationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'EVM Group "{}"'.format(self.obj.description)
        )


class EditGroupView(GroupForm):
    save_button = Button("Save")
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Editing Group "{}"'.format(self.obj.description)
        )


class AllGroupView(ConfigurationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Access Control EVM Groups'
        )


class EditGroupSequenceView(GroupForm):
    title = Text('#explorer_title_text')

    domains = UpDownSelect(
        '#seq_fields',
        './/a[@title="Move selected fields up"]/img',
        './/a[@title="Move selected fields down"]/img')

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == "Editing Sequence of User Groups"
        )


class GroupEditTagsView(ConfigurationView):
    title = Text('#explorer_title_text')

# TODO remove comment, when widget is done
# tag_table = Table("//div[@id='assignments_div']//table")

    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')

    save_button = Button('Save')
    cancel_button = Button('Cancel')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Editing My Company Tags for "EVM Groups"'
        )


class Group(Updateable, Pretty, Navigatable):
    pretty_attrs = ['description', 'role']

    def __init__(self, description=None, role=None, tenant="My Company", user_to_lookup=None,
                 ldap_credentials=None, tag=None, host_cluster=None, vm_template=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.role = role
        self.tenant = tenant
        self.ldap_credentials = ldap_credentials
        self.user_to_lookup = user_to_lookup
        self.tag = tag
        self.host_cluster = host_cluster
        self.vm_template = vm_template

    def create(self):
        view = navigate_to(self, 'Add')
        view.fill({'description_txt': self.description,
                   'role_select': self.role,
                   'group_tenant': self.tenant})
        view.my_company_tags.tag_tree.fill(self.tag)
        view.my_company_tags.hosts_clusters_tree.fill(self.host_cluster)
        view.my_company_tags.vms_templates_tree.fill(self.vm_template)
        view.add_button.click()
        view = self.create_view(AllGroupView)
        view.flash.assert_success_message('Group "{}" was saved'.format(self.description))

    def _retrieve_ldap_user_groups(self):
        view = navigate_to(self, 'Add')
        view.fill({'lookup_ldap_groups_chk': True,
                   'user_to_look_up': self.user_to_lookup,
                   'username': self.ldap_credentials.principal,
                   'password': self.ldap_credentials.secret})
        view.retrieve_button.click()
        return view

    def _retrieve_ext_auth_user_groups(self):
        view = navigate_to(self, 'Add')
        view.fill({'lookup_ldap_groups_chk': True,
                   'user_to_look_up': self.user_to_lookup})
        view.retrieve_button.click()
        return view

    def _fill_ldap_group_lookup(self, view):
        view.fill({'ldap_groups_for_user': self.description,
                   'description_txt': self.description,
                   'role_select': self.role,
                   'group_tenant': self.tenant})
        view.add_button.click()
        view = self.create_view(AllGroupView)
        view.flash.assert_success_message('Group "{}" was saved'.format(self.description))

    def add_group_from_ldap_lookup(self):
        view = self._retrieve_ldap_user_groups()
        self._fill_ldap_group_lookup(view)


    def add_group_from_ext_auth_lookup(self):
        view = self._retrieve_ext_auth_user_groups()
        self._fill_ldap_group_lookup(view)

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        view.fill({'description_txt': updates.get('description'),
                   'role_select': updates.get('role'),
                   'group_tenant': updates.get('tenant')})
        view.save_button.click()
        view = self.create_view(DetailsGroupView)
        view.flash.assert_message(
            'Group "{}" was saved'.format(updates.get('description', self.description)))

    def delete(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this Group', handle_alert=True)
        view = self.create_view(AllGroupView)
        view.flash.assert_success_message(
            'EVM Group "{}": Delete successful'.format(self.description))

    def edit_tags(self, tag, value):
        view = navigate_to(self, 'EditTags')
        view.fill({'select_tag': tag,
                   'select_value': value})
        view.save_button.click()
        view = self.create_view(DetailsGroupView)
        view.flash.assert_success_message('Tag edits were successfully saved')

    def remove_tag(self, tag, value):
        view = navigate_to(self, 'EditTags')
# TODO replace with widget, when ready
        row = tag_table.find_row_by_cells({'category': tag, 'assigned_value': value},
                                          partial_check=True)
        sel.click(row[0])
        view.save_button.click()
        view = self.create_view(DetailsGroupView)
        view.flash.assert_success_message('Tag edits were successfully saved')

    def set_group_order(self, items):
        original_order = get_group_order()
        view = self.create_view(EditGroupSequenceView)
        # We pick only the same amount of items for comparing
        original_order = original_order[:len(items)]
        if items == original_order:
            return  # Ignore that, would cause error on Save click
        view.group_order_selector.fill(items)
        view.save_button.click()

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False


def get_group_order():
    view = navigate_to(Group, 'EditGroupSequence')
    return view.group_order_selector.items


@navigator.register(Group, 'All')
class GroupAll(CFMENavigateStep):
    VIEW = AllGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.view.settings.select_item('Configuration')
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Groups')


@navigator.register(Group, 'Add')
class GroupAdd(CFMENavigateStep):
    VIEW = AddGroupView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a new Group")


@navigator.register(Group, 'EditGroupSequence')
class EditGroupSequence(CFMENavigateStep):
    VIEW = EditGroupSequenceView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select(
            'Edit Sequence of User Groups for LDAP Look Up')


@navigator.register(Group, 'Details')
class GroupDetails(CFMENavigateStep):
    VIEW = DetailsGroupView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Groups', self.obj.description)


@navigator.register(Group, 'Edit')
class GroupEdit(CFMENavigateStep):
    VIEW = EditGroupView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Edit this Group')


@navigator.register(Group, 'EditTags')
class GroupTagsEdit(CFMENavigateStep):
    VIEW = GroupEditTagsView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.policy.item_select("Edit 'My Company' Tags for this Group")


class RoleForm(ConfigurationView):
    title = Text("#explorer_title_text")

    name_txt = Input('name')
    vm_restriction_select = BootstrapSelect('vm_restriction')
    product_features_tree = CheckableBootstrapTreeview("features_treebox")

    cancel_button = Button('Cancel')


class AddRoleView(RoleForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Adding a new Role'
        )


class EditRoleView(RoleForm):
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Editing Role "{}"'.format(self.obj.name)
        )


class DetailsRoleView(RoleForm):
    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Role "{}"'.format(self.obj.name)
        )


class AllRolesView(ConfigurationView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Access Control Roles'
        )


class Role(Updateable, Pretty, Navigatable):
    pretty_attrs = ['name', 'product_features']

    def __init__(self, name=None, vm_restriction=None, product_features=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.vm_restriction = vm_restriction
        self.product_features = product_features or []

    def create(self):
        view = navigate_to(self, 'Add')
        view.fill({'name_txt': self.name,
                   'vm_restriction_select': self.vm_restriction,
                   'product_features_tree': self.product_features})
        view.add_button.click()
        view = self.create_view(AllRolesView)
        view.flash.assert_success_message('Role "{}" was saved'.format(self.name))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        view.fill({'name_txt': updates.get('name'),
                   'vm_restriction_select': updates.get('vm_restriction'),
                   'product_features_tree': updates.get('product_features')})
        view.save_button.click()
        view = self.create_view(DetailsRoleView)
        view.flash.assert_success_message(
            'Role "{}" was saved'.format(updates.get('name', self.name)))

    def delete(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this Role', handle_alert=True)
        view = self.create_view(AllRolesView)
        view.flash.assert_success_message('Role "{}": Delete successful'.format(self.name))

    def copy(self, name=None):
        if not name:
            name = self.name + "copy"
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Copy this Role to a new Role')
        view = self.create_view(AddRoleView)
        new_role = Role(name=name)
        view.fill({'name_txt': new_role.name})
        view.add_button.click()
        view = self.create_view(AllRolesView)
        view.flash.assert_success_message('Role "{}" was saved'.format(new_role.name))
        return new_role


@navigator.register(Role, 'All')
class RoleAll(CFMENavigateStep):
    VIEW = AllRolesView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.view.settings.select_item('Configuration')
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Roles')


@navigator.register(Role, 'Add')
class RoleAdd(CFMENavigateStep):
    VIEW = AddRoleView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a new Role")


@navigator.register(Role, 'Details')
class RoleDetails(CFMENavigateStep):
    VIEW = DetailsRoleView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Roles', self.obj.name)


@navigator.register(Role, 'Edit')
class RoleEdit(CFMENavigateStep):
    VIEW = EditRoleView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.configuration.item_select('Edit this Role')


class TenantForm(ConfigurationView):
    title = Text("#explorer_title_text")

    name = Input(name='name')
    description = Input(name='description')

    cancel_button = Button('Cancel')


class TenantQuotaView(ConfigurationView):
    title = Text("#explorer_title_text")

    cpu_cb = BootstrapSwitch('cpu_allocated')
    memory_cb = BootstrapSwitch('mem_allocated')
    storage_cb = BootstrapSwitch('storage_allocated')
    vm_cb = BootstrapSwitch('vms_allocated')
    template_cb = BootstrapSwitch('templates_allocated')
    cpu_txt = Input('id_cpu_allocated')
    memory_txt = Input('id_mem_allocated')
    storage_txt = Input('id_storage_allocated')
    vm_txt = Input('id_vms_allocated')
    template_txt = Input('id_templates_allocated')

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')


class AllTenantView(ConfigurationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Access Control Tenants'
        )


class AddTenantView(TenantForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Adding a new Tenant'
        )


class DetailsTenantView(ConfigurationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Tenant "{}"'.format(self.obj.name)
        )


class EditTenantView(TenantForm):
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_configuration and self.access_control.is_opened and
            self.title.text == 'Editing Tenant "{}"'.format(self.obj.name)
        )


class Tenant(Updateable, Pretty, Navigatable):
    """ Class representing CFME tenants in the UI.
    * Kudos to mfalesni *

    The behaviour is shared with Project, which is the same except it cannot create more nested
    tenants/projects.

    Args:
        name: Name of the tenant
        description: Description of the tenant
        parent_tenant: Parent tenant, can be None, can be passed as string or object
    """
    pretty_attrs = ["name", "description"]

    @classmethod
    def get_root_tenant(cls):
        return cls(name="My Company", _default=True)

    def __init__(self, name=None, description=None, parent_tenant=None, _default=False,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.parent_tenant = parent_tenant
        self._default = _default

    @property
    def parent_tenant(self):
        if self._default:
            return None
        if self._parent_tenant:
            return self._parent_tenant
        return self.get_root_tenant()

    @parent_tenant.setter
    def parent_tenant(self, tenant):
        if tenant is not None and isinstance(tenant, Project):
            # If we try to
            raise ValueError("Project cannot be a parent object.")
        if isinstance(tenant, basestring):
            # If parent tenant is passed as string,
            # we assume that tenant name was passed instead of object
            tenant = Tenant(tenant)
        self._parent_tenant = tenant

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        else:
            return self.name == other.name

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
        return self.tree_path[:-1]

    def create(self, cancel=False):
        if self._default:
            raise ValueError("Cannot create the root tenant {}".format(self.name))

        view = navigate_to(self, 'Add')
        view.fill({'name': self.name,
                   'description': self.description})
        view.add_button.click()
        view = view.create(DetailsTenantView)
        if type(self) is Tenant:
            view.flash.assert_success_message('Tenant "{}" was saved'.format(self.name))
        elif type(self) is Project:
            view.flash.assert_success_message('Project "{}" was saved'.format(self.name))
        else:
            raise TypeError(
                'No Tenant or Project class passed to create method{}'.format(
                    type(self).__name__))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        view.fill({'name': updates.get('name'),
                   'description': updates.get('description')})
        view.save_button.click()
        view = view.create(DetailsTenantView)
        view.flash.assert_success_message(
            'Project "{}" was saved'.format(updates.get('name', self.name)))

    def delete(self, cancel=False):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this item', handle_alert=True)
        view = view.create(DetailsTenantView)
        view.flash.assert_success_message('Tenant "{}": Delete successful'.format(self.description))

    def set_quota(self, **kwargs):
        view = navigate_to(self, 'ManageQuotas')
        view.fill({'cpu_cb': kwargs.get('cpu_cb'),
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
        view = view.create(DetailsTenantView)
        view.flash.assert_success_message('Quotas for Tenant "{}" were saved'.format(self.name))


@navigator.register(Tenant, 'All')
class TenantAll(CFMENavigateStep):
    VIEW = AllTenantView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.view.settings.select_item('Configuration')
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Tenants')


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    VIEW = DetailsTenantView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.access_control.tree.click_path(
            self.obj.appliance.server_region_string(), 'Tenants', *self.obj.tree_path)


@navigator.register(Tenant, 'Add')
class TenantAdd(CFMENavigateStep):
    VIEW = AddTenantView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        import pdb
        pdb.set_trace()
        self.view.access_control.tree.click_path(self.obj.appliance.server_region_string(),
                                                 'Tenants', *self.obj.parent_path)
        if isinstance(self.obj, Tenant):
            add_selector = 'Add child Tenant to this Tenant'
        elif isinstance(self.obj, Project):
            add_selector = 'Add Project to this Tenant'
        else:
            raise OptionNotAvailable('Object type unsupported for Tenant Add: {}'
                                     .format(type(self.obj).__name__))
        self.view.configuration.item_select(add_selector)


@navigator.register(Tenant, 'Edit')
class TenantEdit(CFMENavigateStep):
    VIEW = EditTenantView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.view.configuration.item_select('Edit this item')


@navigator.register(Tenant, 'ManageQuotas')
class TenantManageQuotas(CFMENavigateStep):
    VIEW = TenantQuotaView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.view.configuration.item_select('Manage Quotas')


class Project(Tenant):
    """ Class representing CFME projects in the UI.

    Project cannot create more child tenants/projects.

    Args:
        name: Name of the project
        description: Description of the project
        parent_tenant: Parent project, can be None, can be passed as string or object
    """
    pass
