from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import UpDownSelect, SummaryFormItem
from widgetastic_patternfly import (
    BootstrapSelect, Button, Input, Tab, CheckableBootstrapTreeview,
    BootstrapSwitch, CandidateNotFound, Dropdown)
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import Checkbox, View, Table, Text

from cfme.base.credential import Credential
from cfme.base.ui import ConfigurationView
from cfme.exceptions import OptionNotAvailable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.log import logger
from utils.pretty import Pretty
from utils.update import Updateable
from utils.wait import wait_for


def simple_user(userid, password):
    creds = Credential(principal=userid, secret=password)
    return User(name=userid, credential=creds)


class UserForm(ConfigurationView):
    """ User Form View."""
    name_txt = Input(name='name')
    userid_txt = Input(name='userid')
    password_txt = Input(id='password')
    password_verify_txt = Input(id='verify')
    email_txt = Input(name='email')
    user_group_select = BootstrapSelect(id='chosen_group')

    cancel_button = Button('Cancel')


class UsersEntities(View):
    table = Table('//div[@id=\'records_div\']//table')


class AllUserView(ConfigurationView):
    """ All Users View."""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    entities = View.nested(UsersEntities)

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Access Control EVM Users'
        )


class AddUserView(UserForm):
    """ Add User View."""
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return self.accordions.accesscontrol.is_opened and self.title.text == "Adding a new User"


class DetailsUserView(ConfigurationView):
    """ User Details view."""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    @property
    def is_displayed(self):
        return (
            self.title.text == 'EVM User "{}"'.format(self.context['object'].name) and
            self.accordions.accesscontrol.is_opened
        )


class EditUserView(UserForm):
    """ User Edit View."""
    save_button = Button('Save')
    reset_button = Button('Reset')
    change_stored_password = Text('#change_stored_password')
    cancel_password_change = Text('#cancel_password_change')

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Editing User "{}"'.format(self.context['object'].name) and
            self.accordions.accesscontrol.is_opened
        )


class EditTagsUserView(ConfigurationView):
    """ Tags edit for Users view."""
    tag_table = Table("//div[@id='assignments_div']//table")
    select_tag = BootstrapSelect(id='tag_cat')
    select_value = BootstrapSelect(id='tag_add')

    save_button = Button('Save')
    cancel_button = Button('Cancel')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Editing My Company Tags for "EVM Users"'
        )


class User(Updateable, Pretty, Navigatable):
    """ Class represents an user in CFME UI
        Args:
            name: Name of the user
            credential: User's credentials
            email: User's email
            group: User's group for assigment
            cost_center: User's cost center
            value_assign: user's value to assign
            appliance: appliance under test
    """
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

    def create(self, cancel=False):
        """ User creation method
        Args:
            cancel: True - if you want to cancel user creation,
                    by defaul user will be created
        """
        view = navigate_to(self, 'Add')
        view.fill({
            'name_txt': self.name,
            'userid_txt': self.credential.principal,
            'password_txt': self.credential.secret,
            'password_verify_txt': self.credential.verify_secret,
            'email_txt': self.email,
            'user_group_select': getattr(self.group, 'description', None)
        })
        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new User was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'User "{}" was saved'.format(self.name)
        view = self.create_view(AllUserView)
        view.flash.assert_success_message(flash_message)
        assert view.is_displayed

    def update(self, updates):
        """ Update user method
            Args:
                updates: user data that should be changed
        Note: In case updates is the same as original user data, update will be canceled,
        as 'Save' button will not be active
        """
        view = navigate_to(self, 'Edit')
        self.change_stored_password()
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
        changed = view.fill({
            'name_txt': new_updates.get('name_txt'),
            'userid_txt': new_updates.get('userid_txt'),
            'password_txt': new_updates.get('password_txt'),
            'password_verify_txt': new_updates.get('password_verify_txt'),
            'email_txt': new_updates.get('email_txt'),
            'user_group_select': new_updates.get('user_group_select')
        })
        if changed:
            view.save_button.click()
            flash_message = 'User "{}" was saved'.format(updates.get('name', self.name))
        else:
            view.cancel_button.click()
            flash_message = 'Edit of User was cancelled by the user'
        view = self.create_view(DetailsUserView, override=updates)
        view.flash.assert_message(flash_message)
        assert view.is_displayed

    def copy(self):
        """ Creates copy of existing user
            return: User object of copied user
        """
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Copy this User to a new User')
        view = self.create_view(AddUserView)
        new_user = User(name="{}copy".format(self.name),
                        credential=Credential(principal='redhat', secret='redhat'))
        view.fill({
            'name_txt': new_user.name,
            'userid_txt': new_user.credential.principal,
            'password_txt': new_user.credential.secret,
            'password_verify_txt': new_user.credential.verify_secret
        })
        view.add_button.click()
        view = self.create_view(AllUserView)
        view.flash.assert_success_message('User "{}" was saved'.format(new_user.name))
        assert view.is_displayed
        return new_user

    def delete(self, cancel=True):
        """ Delete existing user
            Args:
                cancel: Default value 'True', user will be deleted
                        'False' - deletion of user will be canceled
        """
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this User', handle_alert=cancel)
        if cancel:
            view = self.create_view(AllUserView)
            view.flash.assert_success_message('EVM User "{}": Delete successful'.format(self.name))
        else:
            view = self.create_view(DetailsUserView)
        assert view.is_displayed

    def edit_tags(self, tag, value):
        """ Edits tag for existing user
            Args:
                tag: Tag category
                value: Tag name
        """
        view = navigate_to(self, 'EditTags')
        view.fill({'select_tag': tag,
                   'select_value': value})
        view.save_button.click()
        view = self.create_view(DetailsUserView)
        view.flash.assert_success_message('Tag edits were successfully saved')
        assert view.is_displayed

    def remove_tag(self, tag, value):
        """ Remove tag from existing user
            Args:
                tag: Tag category
                value: Tag name
        """
        view = navigate_to(self, 'EditTags')
        row = view.tag_table.row(category=tag, assigned_value=value)
        row[0].click()
        view.save_button.click()
        view = self.create_view(DetailsUserView)
        view.flash.assert_success_message('Tag edits were successfully saved')
        assert view.is_displayed

# TODO update elements, after 1469035 fix
    def change_stored_password(self, changes=None, cancel=False):
        """ Changes user password
         Args:
             changes: dict with fields to be changes,
                      if None, passwords fields only be anabled
             cancel: True, if you want to disable password change
        """
        view = navigate_to(self, 'Edit')
        self.browser.execute_script(
            self.browser.get_attribute(
                'onClick', self.browser.element(view.change_stored_password)))
        if changes:
            view.fill(changes)
        if cancel:
            self.browser.execute_script(
                self.browser.get_attribute(
                    'onClick', self.browser.element(view.cancel_password_change)))

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
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Users')


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
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Users', self.obj.name)


@navigator.register(User, 'Edit')
class UserEdit(CFMENavigateStep):
    VIEW = EditUserView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this User')


@navigator.register(User, 'EditTags')
class UserTagsEdit(CFMENavigateStep):
    VIEW = EditTagsUserView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy.item_select("Edit 'My Company' Tags for this User")


class GroupForm(ConfigurationView):
    """ Group Form in CFME UI."""
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
        """ Represents 'My company tags' tab in Group Form """
        TAB_NAME = "My Company Tags"
        tree_locator = VersionPick({
            Version.lowest(): 'tagsbox',
            '5.8': 'tags_treebox'}
        )
        tree = CheckableBootstrapTreeview(tree_locator)

    @View.nested
    class hosts_and_clusters(Tab):      # noqa
        """ Represents 'Hosts and Clusters' tab in Group Form """
        TAB_NAME = "Hosts & Clusters"
        tree = CheckableBootstrapTreeview('hac_treebox')

    @View.nested
    class vms_and_templates(Tab):       # noqa
        """ Represents 'VM's and Templates' tab in Group Form """
        TAB_NAME = "VMs & Templates"
        tree = CheckableBootstrapTreeview('vat_treebox')


class AddGroupView(GroupForm):
    """ Add Group View in CFME UI """
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == "Adding a new Group"
        )


class DetailsGroupView(ConfigurationView):
    """ Details Group View in CFME UI """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'EVM Group "{}"'.format(self.context['object'].description)
        )


class EditGroupView(GroupForm):
    """ Edit Group View in CFME UI """
    save_button = Button("Save")
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Editing Group "{}"'.format(self.context['object'].description)
        )


class AllGroupView(ConfigurationView):
    """ All Groups View in CFME UI """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    table = Table("//div[@id='main_div']//table")

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Access Control EVM Groups'
        )


class EditGroupSequenceView(ConfigurationView):
    """ Edit Groups Sequence View in CFME UI """
    group_order_selector = UpDownSelect(
        '#seq_fields',
        './/a[@title="Move selected fields up"]/img',
        './/a[@title="Move selected fields down"]/img')

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == "Editing Sequence of User Groups"
        )


class GroupEditTagsView(ConfigurationView):
    """ Edit Groups Tags View in CFME UI """
    tag_table = Table("//div[@id='assignments_div']//table")

    select_tag = BootstrapSelect(id='tag_cat')
    select_value = BootstrapSelect(id='tag_add')

    save_button = Button('Save')
    cancel_button = Button('Cancel')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Editing My Company Tags for "EVM Groups"'
        )


class Group(Updateable, Pretty, Navigatable):
    """Represents a group in CFME UI
        Args:
            description: group description
            role: group role
            tenant: group tenant
            user_to_lookup: ldap user to lookup
            ldap_credentials: ldap user credentials
            tag: tag for group restriction
            host_cluster: host/cluster for group restriction
            vm_template: vm/template for group restriction
            appliance: appliance under test
    """
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

    def create(self, cancel=False):
        """ Create group method
            Args:
                cancel: True - if you want to cancel group creation,
                        by defaul group will be created
        """
        view = navigate_to(self, 'Add')
        view.fill({
            'description_txt': self.description,
            'role_select': self.role,
            'group_tenant': self.tenant
        })
        self._set_group_restriction(view.my_company_tags, self.tag)
        self._set_group_restriction(view.hosts_and_clusters, self.host_cluster)
        self._set_group_restriction(view.vms_and_templates, self.vm_template)
        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Group was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Group "{}" was saved'.format(self.description)
        view = self.create_view(AllGroupView)
        view.flash.assert_success_message(flash_message)
        assert view.is_displayed

    def _retrieve_ldap_user_groups(self):
        """ Retrive ldap user groups
            return: AddGroupView
        """
        view = navigate_to(self, 'Add')
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
        view = navigate_to(self, 'Add')
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

    def add_group_from_ldap_lookup(self):
        """Adds a group from ldap lookup"""
        view = self._retrieve_ldap_user_groups()
        self._fill_ldap_group_lookup(view)

    def add_group_from_ext_auth_lookup(self):
        """Adds a group from external authorization lookup"""
        view = self._retrieve_ext_auth_user_groups()
        self._fill_ldap_group_lookup(view)

    def update(self, updates):
        """ Update group method
            Args:
                updates: group data that should be changed
        Note: In case updates is the same as original group data, update will be canceled,
        as 'Save' button will not be active
        """
        view = navigate_to(self, 'Edit')
        changed = view.fill({
            'description_txt': updates.get('description'),
            'role_select': updates.get('role'),
            'group_tenant': updates.get('tenant')
        })
        changed_tag = self._set_group_restriction(view.my_company_tags, updates.get('tag'), True)
        changed_host_cluster = self._set_group_restriction(
            view.hosts_and_clusters, updates.get('host_cluster'), True)
        changed_vm_template = self._set_group_restriction(
            view.vms_and_templates, updates.get('vm_template'), True)

        if changed or changed_tag or changed_host_cluster or changed_vm_template:
            view.save_button.click()
            flash_message = 'Group "{}" was saved'.format(
                updates.get('description', self.description))
        else:
            view.cancel_button.click()
            flash_message = 'Edit of Group was cancelled by the user'
        view = self.create_view(DetailsGroupView, override=updates)
        view.flash.assert_message(flash_message)
        assert view.is_displayed

    def delete(self, cancel=True):
        """ Delete existing group
            Args:
                cancel: Default value 'True', group will be deleted
                        'False' - deletion of group will be canceled
        """
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this Group', handle_alert=cancel)
        if cancel:
            view = self.create_view(AllGroupView)
            view.flash.assert_success_message(
                'EVM Group "{}": Delete successful'.format(self.description))
        else:
            view = self.create_view(DetailsGroupView)
        assert view.is_displayed

    def edit_tags(self, tag, value):
        """ Edits tag for existing group
            Args:
                tag: Tag category
                value: Tag name
        """
        view = navigate_to(self, 'EditTags')
        view.fill({'select_tag': tag,
                   'select_value': value})
        view.save_button.click()
        view = self.create_view(DetailsGroupView)
        view.flash.assert_success_message('Tag edits were successfully saved')
        assert view.is_displayed

    def remove_tag(self, tag, value):
        """ Delete tag for existing group
            Args:
                tag: Tag category
                value: Tag name
        """
        view = navigate_to(self, 'EditTags')
        row = view.tag_table.row(category=tag, assigned_value=value)
        row[0].click()
        view.save_button.click()
        view = self.create_view(DetailsGroupView)
        view.flash.assert_success_message('Tag edits were successfully saved')
        assert view.is_displayed

    def set_group_order(self, updated_order):
        """ Sets group order for group lookup
            Args:
                updated_order: group order list
        """
        original_order = self.group_order[:len(updated_order)]
        view = self.create_view(EditGroupSequenceView)
        assert view.is_displayed
        # We pick only the same amount of items for comparing
        if updated_order == original_order:
            return  # Ignore that, would cause error on Save click
        view.group_order_selector.fill(updated_order)
        view.save_button.click()

    def _set_group_restriction(self, tab_view, item, update=False):
        """ Sets tag/host/template restriction for the group
            Args:
                tab_view: tab view
                item: path to check box that should be selected/deselected
                update: If True - checkbox state will be updated
            return: True - if update is successful
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
        view = navigate_to(Group, 'EditGroupSequence')
        return view.group_order_selector.items

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False


@navigator.register(Group, 'All')
class GroupAll(CFMENavigateStep):
    VIEW = AllGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Groups')


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
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Groups', self.obj.description)


@navigator.register(Group, 'Edit')
class GroupEdit(CFMENavigateStep):
    VIEW = EditGroupView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Group')


@navigator.register(Group, 'EditTags')
class GroupTagsEdit(CFMENavigateStep):
    VIEW = GroupEditTagsView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy.item_select("Edit 'My Company' Tags for this Group")


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
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Role "{}"'.format(self.context['object'].name)
        )


class AllRolesView(ConfigurationView):
    """ All Roles View """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Access Control Roles'
        )


class Role(Updateable, Pretty, Navigatable):
    """ Represents a role in CFME UI
        Args:
            name: role name
            vm_restriction: restriction used for role
            product_features: product feature to select
            appliance: appliance unter test
    """

    pretty_attrs = ['name', 'product_features']

    def __init__(self, name=None, vm_restriction=None, product_features=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.vm_restriction = vm_restriction
        self.product_features = product_features or []

    def create(self, cancel=False):
        """ Create role method
            Args:
                cancel: True - if you want to cancel role creation,
                        by defaul, role will be created
        """
        view = navigate_to(self, 'Add')
        view.fill({'name_txt': self.name,
                   'vm_restriction_select': self.vm_restriction})
        self.set_role_product_features(view, self.product_features)
        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Role was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Role "{}" was saved'.format(self.name)
        view = self.create_view(AllRolesView)
        view.flash.assert_success_message(flash_message)
        assert view.is_displayed

    def update(self, updates):
        """ Update role method
            Args:
                updates: role data that should be changed
        Note: In case updates is the same as original role data, update will be canceled,
        as 'Save' button will not be active
        """
        view = navigate_to(self, 'Edit')
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
        """
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this Role', handle_alert=cancel)
        if cancel:
            view = self.create_view(AllRolesView)
            view.flash.assert_success_message('Role "{}": Delete successful'.format(self.name))
        else:
            view = self.create_view(DetailsRoleView)
        assert view.is_displayed

    def copy(self, name=None):
        """ Creates copy of existing role
            return: Role object of copied role
        """
        if name is None:
            name = "{}_copy".format(self.name)
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Copy this Role to a new Role')
        view = self.create_view(AddRoleView)
        new_role = Role(name=name)
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


@navigator.register(Role, 'All')
class RoleAll(CFMENavigateStep):
    VIEW = AllRolesView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Roles')


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
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Roles', self.obj.name)


@navigator.register(Role, 'Edit')
class RoleEdit(CFMENavigateStep):
    VIEW = EditRoleView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Role')


class TenantForm(ConfigurationView):
    """ Tenant Form """
    name = Input(name='name')
    description = Input(name='description')

    cancel_button = Button('Cancel')


class TenantQuotaView(ConfigurationView):
    """ Tenant Quota View """
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

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')


class AllTenantView(ConfigurationView):
    """ All Tenants View """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Access Control Tenants'
        )


class AddTenantView(TenantForm):
    """ Add Tenant View """
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Adding a new Tenant'
        )


class DetailsTenantView(ConfigurationView):
    """ Details Tenant View """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Tenant "{}"'.format(self.context['object'].name)
        )


class ParentDetailsTenantView(DetailsTenantView):
    """ Parent Tenant Details View """
    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Tenant "{}"'.format(self.context['object'].parent_tenant.name)
        )


class EditTenantView(TenantForm):
    """ Edit Tenant View """
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'Editing Tenant "{}"'.format(self.context['object'].name)
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
        """ Create role method
            Args:
                cancel: True - if you want to cancel role creation,
                        by defaul(False), role will be created
        """
        if self._default:
            raise ValueError("Cannot create the root tenant {}".format(self.name))

        view = navigate_to(self, 'Add')
        view.fill({'name': self.name,
                   'description': self.description})
        if cancel:
            view.cancel_button.click()
            tenant_flash_message = 'Add of new Tenant was cancelled by the user'
            project_flash_message = 'Add of new Project was cancelled by the user'
        else:
            view.add_button.click()
            tenant_flash_message = 'Tenant "{}" was saved'.format(self.name)
            project_flash_message = 'Project "{}" was saved'.format(self.name)
        view = self.create_view(ParentDetailsTenantView)
        if isinstance(self, Tenant):
            view.flash.assert_success_message(tenant_flash_message)
        elif isinstance(self, Project):
            view.flash.assert_success_message(project_flash_message)
        else:
            raise TypeError(
                'No Tenant or Project class passed to create method{}'.format(
                    type(self).__name__))
        assert view.is_displayed

    def update(self, updates):
        """ Update tenant/project method
            Args:
                updates: tenant/project data that should be changed
        Note: In case updates is the same as original tenant/project data, update will be canceled,
        as 'Save' button will not be active
        """
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
            flash_message = 'Project "{}" was saved'.format(updates.get('name', self.name))
        else:
            view.cancel_button.click()
            flash_message = 'Edit of Project "{}" was cancelled by the user'.format(
                updates.get('name', self.name))
        view = self.create_view(DetailsTenantView, override=updates)
        view.flash.assert_message(flash_message)
        assert view.is_displayed

    def delete(self, cancel=True):
        """ Delete existing role
            Args:
                cancel: Default value 'True', role will be deleted
                        'False' - deletion of role will be canceled
        """
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete this item', handle_alert=cancel)
        if cancel:
            view = self.create_view(ParentDetailsTenantView)
            view.flash.assert_success_message(
                'Tenant "{}": Delete successful'.format(self.description))
        else:
            view = self.create_view(DetailsRoleView)
        assert view.is_displayed

    def set_quota(self, **kwargs):
        """ Sets tenant quotas """
        view = navigate_to(self, 'ManageQuotas')
        wait_for(lambda: view.is_displayed, fail_condition=False, num_sec=5, delay=0.5)
        # TODO : fill happens before the page is fully loaded,
        # resolve this so the wait_for is not needed
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
        view = self.create_view(DetailsTenantView)
        view.flash.assert_success_message('Quotas for Tenant "{}" were saved'.format(self.name))
        assert view.is_displayed


@navigator.register(Tenant, 'All')
class TenantAll(CFMENavigateStep):
    VIEW = AllTenantView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Tenants')


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    VIEW = DetailsTenantView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Tenants', *self.obj.tree_path)


@navigator.register(Tenant, 'Add')
class TenantAdd(CFMENavigateStep):
    VIEW = AddTenantView

    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Tenants', *self.obj.parent_path)
        if isinstance(self.obj, Tenant):
            add_selector = 'Add child Tenant to this Tenant'
        elif isinstance(self.obj, Project):
            add_selector = 'Add Project to this Tenant'
        else:
            raise OptionNotAvailable('Object type unsupported for Tenant Add: {}'
                                     .format(type(self.obj).__name__))
        self.prerequisite_view.configuration.item_select(add_selector)


@navigator.register(Tenant, 'Edit')
class TenantEdit(CFMENavigateStep):
    VIEW = EditTenantView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this item')


@navigator.register(Tenant, 'ManageQuotas')
class TenantManageQuotas(CFMENavigateStep):
    VIEW = TenantQuotaView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Manage Quotas')


class Project(Tenant):
    """ Class representing CFME projects in the UI.

    Project cannot create more child tenants/projects.

    Args:
        name: Name of the project
        description: Description of the project
        parent_tenant: Parent project, can be None, can be passed as string or object
    """
    pass
