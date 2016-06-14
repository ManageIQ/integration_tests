from functools import partial
from cfme import Credential
from fixtures.pytest_store import store
import cfme
from cfme.exceptions import CandidateNotFound
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui.form_buttons import change_stored_password
from cfme.web_ui import AngularSelect, Form, Select, CheckboxTree, accordion, fill, flash, \
    form_buttons, Input, Table, UpDownSelect
from cfme.web_ui.menu import extend_nav, nav
from utils.log import logger
from utils.update import Updateable
from utils import version
from utils.pretty import Pretty

from configuration import server_region_string

tb_select = partial(tb.select, "Configuration")
pol_btn = partial(tb.select, "Policy")

edit_tags_form = Form(
    fields=[
        ("select_tag", Select("select#tag_cat")),
        ("select_value", Select("select#tag_add"))
    ])

tag_table = Table("//div[@id='assignments_div']//table")

group_order_selector = UpDownSelect(
    "select#seq_fields",
    "//img[@alt='Move selected fields up']",
    "//img[@alt='Move selected fields down']")

nav.add_branch(
    'configuration',
    {
        'cfg_accesscontrol_users':
        [
            lambda d: accordion.tree("Access Control", server_region_string(), "Users"),
            {
                'cfg_accesscontrol_user_add':
                lambda d: tb_select("Add a new User")
            }
        ],

        'cfg_accesscontrol_user_ed':
        [
            lambda ctx:
            accordion.tree("Access Control", server_region_string(), "Users", ctx.user.name),
            {
                'cfg_accesscontrol_user_edit':
                lambda d: tb_select('Edit this User')
            }
        ],

        'cfg_accesscontrol_groups':
        [
            lambda d: accordion.tree("Access Control", server_region_string(), "Groups"),
            {
                'cfg_accesscontrol_group_add':
                lambda d: tb_select("Add a new Group"),

                'cfg_accesscontrol_group_edit_seq':
                lambda d: tb_select('Edit Sequence of User Groups for LDAP Look Up')
            }
        ],

        'cfg_accesscontrol_group_ed':
        [
            lambda ctx: accordion.tree(
                "Access Control", server_region_string(), "Groups", ctx.group.description),
            {
                'cfg_accesscontrol_group_edit':
                lambda d: tb_select('Edit this Group')
            }
        ],


        'cfg_accesscontrol_Roles':
        [
            lambda d: accordion.tree("Access Control", server_region_string(), "Roles"),
            {
                'cfg_accesscontrol_role_add':
                lambda d: tb_select("Add a new Role")
            }
        ],

        'cfg_accesscontrol_role_ed':
        [
            lambda ctx:
            accordion.tree("Access Control", server_region_string(), "Roles", ctx.role.name),
            {
                'cfg_accesscontrol_role_edit':
                lambda d: tb_select('Edit this Role')
            }
        ],

        'chargeback_assignments':
        nav.fn(partial(accordion.click, "Assignments"))
    }
)


@extend_nav
class configuration:
    def cfg_tenant_project_create(context):
        tenant = context["tenant"]
        if tenant._default:
            raise ValueError("Cannot create the root tenant {}".format(tenant.name))
        accordion.tree("Access Control", server_region_string(), "Tenants", *tenant.parent_path)
        if type(tenant) is Tenant:
            tb_select("Add child Tenant to this Tenant")
        elif type(tenant) is Project:
            tb_select("Add Project to this Tenant")
        else:
            raise TypeError(
                'You must pass either Tenant or Project class but not {}'.format(
                    type(tenant).__name__))

    class cfg_tenant_project:
        def navigate(context):
            tenant = context["tenant"]
            accordion.tree("Access Control", server_region_string(), "Tenants", *tenant.tree_path)

        def cfg_tenant_project_edit(_):
            tb_select("Edit this item")
            sel.wait_for_ajax()


def simple_user(userid, password):
    creds = Credential(principal=userid, secret=password)
    return User(name=userid, credential=creds)


class User(Updateable, Pretty):
    user_form = Form(
        fields=[
            ('name_txt', Input('name')),
            ('userid_txt', Input('userid')),
            ('password_txt', Input('password')),
            ('password_verify_txt', {version.LOWEST: Input('password2'),
                                     "5.5": Input('verify')}),
            ('email_txt', Input('email')),
            ('user_group_select', Select("//*[@id='chosen_group']")),
        ])

    pretty_attrs = ['name', 'group']

    def __init__(self, name=None, credential=None, email=None,
                 group=None, cost_center=None, value_assign=None):
        self.name = name
        self.credential = credential
        self.email = email
        self.group = group
        self.cost_center = cost_center
        self.value_assign = value_assign
        self._restore_user = None

    def __enter__(self):
        if self._restore_user != store.user:
            from cfme.login import logout
            logger.info('Switching to new user: %s', self.credential.principal)
            self._restore_user = store.user
            logout()
            store.user = self

    def __exit__(self, *args, **kwargs):
        if self._restore_user != store.user:
            from cfme.login import logout
            logger.info('Restoring to old user: %s', self._restore_user.credential.principal)
            logout()
            store.user = self._restore_user
            self._restore_user = None

    def create(self):
        sel.force_navigate('cfg_accesscontrol_user_add')
        fill(self.user_form, {'name_txt': self.name,
                              'userid_txt': self.credential.principal,
                              'password_txt': self.credential.secret,
                              'password_verify_txt': self.credential.verify_secret,
                              'email_txt': self.email,
                              'user_group_select': getattr(self.group,
                                                           'description', None)},
             action=form_buttons.add)
        flash.assert_success_message('User "{}" was saved'.format(self.name))

    def update(self, updates):
        sel.force_navigate("cfg_accesscontrol_user_edit", context={"user": self})
        change_stored_password()
        fill(self.user_form, {'name_txt': updates.get('name'),
                              'userid_txt': updates.get('credential').principal,
                              'password_txt': updates.get('credential').secret,
                              'password_verify_txt': updates.get('credential').verify_secret,
                              'email_txt': updates.get('email'),
                              'user_group_select': getattr(updates.get('group'),
                                                           'description', None)},
             action=form_buttons.save)
        flash.assert_success_message(
            'User "{}" was saved'.format(updates.get('name', self.name)))

    def copy(self):
        sel.force_navigate("cfg_accesscontrol_user_ed", context={"user": self})
        tb.select('Configuration', 'Copy this User to a new User')
        new_user = User(name=self.name + "copy",
                        credential=cfme.Credential(principal='redhat', secret='redhat'))
        change_stored_password()
        fill(self.user_form, {'name_txt': new_user.name,
                              'userid_txt': new_user.credential.principal,
                              'password_txt': new_user.credential.secret,
                              'password_verify_txt': new_user.credential.verify_secret},
             action=form_buttons.add)
        flash.assert_success_message('User "{}" was saved'.format(new_user.name))
        return new_user

    def delete(self):
        sel.force_navigate("cfg_accesscontrol_user_ed", context={"user": self})
        tb.select('Configuration', 'Delete this User', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('EVM User "{}": Delete successful'.format(self.name))

    def edit_tags(self, tag, value):
        sel.force_navigate("cfg_accesscontrol_user_ed", context={"user": self})
        pol_btn("Edit 'My Company' Tags for this User", invokes_alert=True)
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')

    def remove_tag(self, tag, value):
        sel.force_navigate("cfg_accesscontrol_user_ed", context={"user": self})
        pol_btn("Edit 'My Company' Tags for this User", invokes_alert=True)
        row = tag_table.find_row_by_cells({'category': tag, 'assigned_value': value},
            partial_check=True)
        sel.click(row[0])
        form_buttons.save()
        flash.assert_success_message('Tag edits were successfully saved')

    @property
    def description(self):
        return self.credential.principal


class Group(Updateable, Pretty):
    group_form = Form(
        fields=[
            ('description_txt', Input('description')),
            ('role_select', {
                version.LOWEST: Select("//*[@id='group_role']"),
                "5.5": AngularSelect("group_role")}),
            ('group_tenant', AngularSelect("group_tenant"), {"appeared_in": "5.5"})
        ])
    pretty_attrs = ['description', 'role']

    def __init__(self, description=None, role=None, tenant="My Company"):
        self.description = description
        self.role = role
        self.tenant = tenant

    def create(self):
        sel.force_navigate('cfg_accesscontrol_group_add')
        fill(self.group_form, {'description_txt': self.description,
                               'role_select': self.role,
                               'group_tenant': self.tenant},
             action=form_buttons.add)
        flash.assert_success_message('Group "{}" was saved'.format(self.description))

    def update(self, updates):
        sel.force_navigate("cfg_accesscontrol_group_edit", context={"group": self})
        fill(self.group_form, {'description_txt': updates.get('description'),
                               'role_select': updates.get('role'),
                               'group_tenant': updates.get('tenant')},
             action=form_buttons.save)
        flash.assert_success_message(
            'Group "{}" was saved'.format(updates.get('description', self.description)))

    def delete(self):
        sel.force_navigate("cfg_accesscontrol_group_ed", context={"group": self})
        tb_select('Delete this Group', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('EVM Group "{}": Delete successful'.format(self.description))

    def edit_tags(self, tag, value):
        sel.force_navigate("cfg_accesscontrol_group_ed", context={"group": self})
        pol_btn("Edit 'My Company' Tags for this Group", invokes_alert=True)
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')

    def remove_tag(self, tag, value):
        sel.force_navigate("cfg_accesscontrol_group_ed", context={"group": self})
        pol_btn("Edit 'My Company' Tags for this Group", invokes_alert=True)
        row = tag_table.find_row_by_cells({'category': tag, 'assigned_value': value},
            partial_check=True)
        sel.click(row[0])
        form_buttons.save()
        flash.assert_success_message('Tag edits were successfully saved')


def get_group_order():
    sel.force_navigate("cfg_accesscontrol_group_edit_seq")
    return group_order_selector.get_items()


def set_group_order(items):
    original_order = get_group_order()
    # We pick only the same amount of items for comparing
    original_order = original_order[:len(items)]
    if items == original_order:
        return  # Ignore that, would cause error on Save click
    fill(group_order_selector, items)
    sel.click(form_buttons.save)


class Role(Updateable, Pretty):
    form = Form(
        fields=[
            ('name_txt', Input('name')),
            ('vm_restriction_select', Select("//*[@id='vm_restriction']")),
            ('product_features_tree', CheckboxTree("//div[@id='features_treebox']/ul")),
        ])
    pretty_attrs = ['name', 'product_features']

    def __init__(self, name=None, vm_restriction=None, product_features=None):
        self.name = name
        self.vm_restriction = vm_restriction
        self.product_features = product_features or []

    def create(self):
        sel.force_navigate('cfg_accesscontrol_role_add')
        fill(self.form, {'name_txt': self.name,
                         'vm_restriction_select': self.vm_restriction,
                         'product_features_tree': self.product_features},
             action=form_buttons.add)
        flash.assert_success_message('Role "{}" was saved'.format(self.name))

    def update(self, updates):
        sel.force_navigate("cfg_accesscontrol_role_edit", context={"role": self})
        fill(self.form, {'name_txt': updates.get('name'),
                         'vm_restriction_select': updates.get('vm_restriction'),
                         'product_features_tree': updates.get('product_features')},
             action=form_buttons.save)
        flash.assert_success_message('Role "{}" was saved'.format(updates.get('name', self.name)))

    def delete(self):
        sel.force_navigate("cfg_accesscontrol_role_ed", context={"role": self})
        tb_select('Delete this Role', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Role "{}": Delete successful'.format(self.name))

    def copy(self, name=None):
        if not name:
            name = self.name + "copy"
        sel.force_navigate("cfg_accesscontrol_role_ed", context={"role": self})
        tb.select('Configuration', 'Copy this Role to a new Role')
        new_role = Role(name=name)
        fill(self.form, {'name_txt': new_role.name},
             action=form_buttons.add)
        flash.assert_success_message('Role "{}" was saved'.format(new_role.name))
        return new_role


class Tenant(Updateable, Pretty):
    """ Class representing CFME tenants in the UI.
    * Kudos to mfalesni *

    The behaviour is shared with Project, which is the same except it cannot create more nested
    tenants/projects.

    Args:
        name: Name of the tenant
        description: Description of the tenant
        parent_tenant: Parent tenant, can be None, can be passed as string or object
    """
    save_changes = form_buttons.FormButton("Save changes")
    tenant_form = Form(
        fields=[
            ('name', Input('name')),
            ('description', Input('description'))
        ])
    pretty_attrs = ["name", "description"]

    @classmethod
    def get_root_tenant(cls):
        return cls(name="My Company", _default=True)

    def __init__(self, name=None, description=None, parent_tenant=None, _default=False):
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
            sel.force_navigate("cfg_tenant_project", context={"tenant": self})
        except CandidateNotFound:
            return False
        else:
            return True

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
        sel.force_navigate("cfg_tenant_project_create", context={"tenant": self})
        fill(self.tenant_form, self, action=form_buttons.add)
        if type(self) is Tenant:
            flash.assert_success_message('Tenant "{}" was saved'.format(self.name))
        elif type(self) is Project:
            flash.assert_success_message('Project "{}" was saved'.format(self.name))
        else:
            raise TypeError(
                'No Tenant or Project class passed to create method{}'.format(
                    type(self).__name__))

    def update(self, updates):
        sel.force_navigate("cfg_tenant_project_edit", context={"tenant": self})
        # Workaround - without this, update was failing sometimes
        sel.wait_for_ajax()
        # Workaround - form is appearing after short delay
        sel.wait_for_element(self.tenant_form.description)
        fill(self.tenant_form, updates, action=self.save_changes)
        flash.assert_success_message(
            'Project "{}" was saved'.format(updates.get('name', self.name)))

    def delete(self, cancel=False):
        sel.force_navigate("cfg_tenant_project", context={"tenant": self})
        tb_select("Delete this item", invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_success_message('Tenant "{}": Delete successful'.format(self.description))


class Project(Tenant):
    """ Class representing CFME projects in the UI.

    Project cannot create more child tenants/projects.

    Args:
        name: Name of the project
        description: Description of the project
        parent_tenant: Parent project, can be None, can be passed as string or object
    """
    pass
