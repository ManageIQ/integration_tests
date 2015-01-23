from copy import deepcopy
from functools import partial
from fixtures.pytest_store import store
from urlparse import urlparse
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, Select, CheckboxTree, accordion, fill, flash, form_buttons
from cfme.web_ui.menu import nav
from utils.update import Updateable
from utils import version
from utils.pretty import Pretty

from utils.smart_resource import SmartResource, InputField, SelectField, PasswordField


def get_ip_address():
    """Returns an IP address of the appliance
    """
    return urlparse(sel.current_url()).netloc


def server_region():
    return store.current_appliance.server_region()


def server_region_pair():
    r = server_region()
    return r, r


def ac_tree(*path):
    """DRY function to access the shared level of the accordion tree.

    Args:
        *path: Path to click in the tree that follows the '[cfme] region xyz' node
    """
    path = version.pick({
        # "5.3": ["CFME Region: Region %d [%d]" % server_region_pair()] + list(path),
        version.LOWEST: path,
    })
    return accordion.tree(
        "Access Control",
        *path
    )

tb_select = partial(tb.select, "Configuration")
# pol_btn = partial(tb.select, "Policy")
nav.add_branch(
    'configuration',
    {
        'configuration_accesscontrol':
        [
            nav.fn(partial(accordion.click, "Access Control")),
            {
                'cfg_accesscontrol_users':
                [
                    lambda d: ac_tree("Users"),
                    {
                        'cfg_accesscontrol_user_add':
                        lambda d: tb.select("Configuration", "Add a new User")
                    }
                ],

                'cfg_accesscontrol_user_ed':
                [
                    lambda ctx: ac_tree('Users', ctx["user"].name),
                    {
                        'cfg_accesscontrol_user_edit':
                        lambda d: tb_select('Edit this User')
                    }
                ],

                'cfg_accesscontrol_groups':
                [
                    lambda d: ac_tree("Groups"),
                    {
                        'cfg_accesscontrol_group_add':
                        lambda d: tb.select("Configuration", "Add a new Group")
                    }
                ],

                'cfg_accesscontrol_group_ed':
                [
                    lambda ctx: ac_tree('Groups', ctx.description),
                    {
                        'cfg_accesscontrol_group_edit':
                        lambda d: tb_select('Edit this Group')
                    }
                ],

                'cfg_accesscontrol_Roles':
                [
                    lambda d: ac_tree("Roles"),
                    {
                        'cfg_accesscontrol_role_add':
                        lambda d: tb.select("Configuration", "Add a new Role")
                    }
                ],

                'cfg_accesscontrol_role_ed':
                [
                    lambda ctx: ac_tree('Roles', ctx.name),
                    {
                        'cfg_accesscontrol_role_edit':
                        lambda d: tb_select('Edit this Role')
                    }
                ],

            }
        ],

        'chargeback_assignments':
        nav.fn(partial(accordion.click, "Assignments"))
    }
)


class User(SmartResource):
    CREATE_LOCATION = "cfg_accesscontrol_user_add"
    EDIT_LOCATION = "cfg_accesscontrol_user_edit"
    DETAIL_LOCATION = "cfg_accesscontrol_user_ed"

    def DELETE_FUNCTION(self):
        tb.select('Configuration', 'Delete this User', invokes_alert=True)
        sel.handle_alert()

    name = InputField(id="name", description="Full user name")
    login = InputField(id="userid", description="Login id")
    password = PasswordField("password", "password2", description="Password used for logging in")
    email = InputField(id="email", description="User's e-mail")
    user_group = SelectField(id="chosen_group", description="The group user belnogs to")

    # Legacy
    user_tag_form = Form(
        fields=[
            ('cost_center_select', Select("//*[@id='tag_cat']")),
            ('value_assign_select', Select("//*[@id='tag_add']")),
        ])

    def post_create(self):
        flash.assert_success_message('User "{}" was saved'.format(self.name))

    def post_update(self):
        flash.assert_success_message('User "{}" was saved'.format(self.name))

    def post_delete(self):
        flash.assert_success_message('EVM User "{}": Delete successful'.format(self.name))

    def copy(self, **data):
        if self.needs_pull:
            self._pull()
        self.go_to_detail()
        tb.select('Configuration', 'Copy this User to a new User')
        new_user_data = deepcopy(self.__data__)
        new_user_data.update(**data)
        new_user = type(self)(**new_user_data)
        new_user.create()
        return new_user


class Group(Updateable, Pretty):
    group_form = Form(
        fields=[
            ('description_txt', "//*[@id='description']"),
            ('role_select', Select("//*[@id='group_role']")),
        ])
    pretty_attrs = ['description', 'role']

    def __init__(self, description=None, role=None):
        self.description = description
        self.role = role

    def create(self):
        sel.force_navigate('cfg_accesscontrol_group_add')
        fill(self.group_form, {'description_txt': self.description,
                               'role_select': self.role},
             action=form_buttons.add)
        flash.assert_success_message('Group "%s" was saved' % self.description)

    def update(self, updates):
        sel.force_navigate("cfg_accesscontrol_group_edit", context=self)
        fill(self.group_form, {'description_txt': updates.get('description'),
                               'role_select': updates.get('role')},
             action=form_buttons.save)
        flash.assert_success_message(
            'Group "%s" was saved' % updates.get('description', self.description))

    def delete(self):
        sel.force_navigate("cfg_accesscontrol_group_ed", context=self)
        tb_select('Delete this Group', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('EVM Group "%s": Delete successful' % self.description)


class Role(Updateable, Pretty):
    form = Form(
        fields=[
            ('name_txt', "//*[@id='name']"),
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
        flash.assert_success_message('Role "%s" was saved' % self.name)

    def update(self, updates):
        sel.force_navigate("cfg_accesscontrol_role_edit", context=self)
        fill(self.form, {'name_txt': updates.get('name'),
                         'vm_restriction_select': updates.get('vm_restriction'),
                         'product_features_tree': updates.get('product_features')},
             action=form_buttons.save)
        flash.assert_success_message('Role "%s" was saved' % updates.get('name', self.name))

    def delete(self):
        sel.force_navigate("cfg_accesscontrol_role_ed", context=self)
        tb_select('Delete this Role', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Role "%s": Delete successful' % self.name)
