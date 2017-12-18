from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import Checkbox, View, Text
from widgetastic_patternfly import (
    BootstrapSelect, Button, Input, Tab, CheckableBootstrapTreeview,
    Dropdown)

from cfme.base.credential import Credential
from cfme.base.ui import ConfigurationView
from cfme.exceptions import RBACOperationBlocked
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from widgetastic_manageiq import (
    UpDownSelect, PaginationPane, SummaryFormItem, Table)
from . import User, UserCollection, Group, GroupCollection


class AccessControlToolbar(View):
    """ Toolbar on the Access Control page """
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


####################################################################################################
# RBAC USER METHODS
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
    table = Table("//div[@id='records_div' or @id='main_div']//table")


class AllUserView(ConfigurationView):
    """ All Users View."""
    toolbar = View.nested(AccessControlToolbar)
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
    toolbar = View.nested(AccessControlToolbar)

    @property
    def is_displayed(self):
        return (
            self.title.text == 'EVM User "{}"'.format(self.context['object'].name) and
            self.accordions.accesscontrol.is_opened and
            # tree.currently_selected returns a list of strings with each item being the text of
            # each level of the accordion. Last element should be the User's name
            self.accordions.accesscontrol.tree.currently_selected[-1] == self.context['object'].name
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


@MiqImplementationContext.external_for(User.update, ViaUI)
def u_update(self, updates):
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


@MiqImplementationContext.external_for(User.copy, ViaUI)
def u_copy(self):
    """ Creates copy of existing user
        return: User object of copied user
    """
    view = navigate_to(self, 'Details')
    view.toolbar.configuration.item_select('Copy this User to a new User')
    view = self.create_view(AddUserView)
    new_user = self.parent.instantiate(
        name="{}copy".format(self.name),
        credential=Credential(principal='redhat', secret='redhat')
    )
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


@MiqImplementationContext.external_for(User.delete, ViaUI)
def u_delete(self, cancel=True):
    """Delete existing user

    Args:
        cancel: Default value 'True', user will be deleted
                'False' - deletion of user will be canceled
    Throws:
        RBACOperationBlocked: If operation is blocked due to current user
            not having appropriate permissions OR delete is not allowed
            for currently selected user
    """
    flash_success_msg = 'EVM User "{}": Delete successful'.format(self.name)
    flash_blocked_msg = "Default EVM User \"{}\" cannot be deleted".format(self.name)
    delete_user_txt = 'Delete this User'

    view = navigate_to(self, 'Details')

    if not view.toolbar.configuration.item_enabled(delete_user_txt):
        raise RBACOperationBlocked("Configuration action '{}' is not enabled".format(
            delete_user_txt))

    view.toolbar.configuration.item_select(delete_user_txt, handle_alert=cancel)
    try:
        view.flash.assert_message(flash_blocked_msg)
        raise RBACOperationBlocked(flash_blocked_msg)
    except AssertionError:
        pass

    view.flash.assert_message(flash_success_msg)

    if cancel:
        view = self.create_view(AllUserView)
        view.flash.assert_success_message(flash_success_msg)
    else:
        view = self.create_view(DetailsUserView)
    assert view.is_displayed


@MiqImplementationContext.external_for(User.edit_tags, ViaUI)
def u_edit_tags(self, tag, value):
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


@MiqImplementationContext.external_for(User.remove_tag, ViaUI)
def u_remove_tag(self, tag, value):
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


@MiqImplementationContext.external_for(User.get_tags, ViaUI)
def u_get_tags(self):
    tags = []
    view = navigate_to(self, 'EditTags')
    for row in view.tag_table:
        tags.append((row.category.text, row.assigned_value.text))
    view.cancel_button.click()
    return tags


# TODO update elements, after 1469035 fix
@MiqImplementationContext.external_for(User.change_stored_password, ViaUI)
def u_change_stored_password(self, changes=None, cancel=False):
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


@MiqImplementationContext.external_for(UserCollection.create, ViaUI)
def uc_create(self, name=None, credential=None, email=None, group=None, cancel=False):
    """ User creation method

    Args:
        name: Name of the user
        credential: User's credentials
        email: User's email
        group: User's group for assigment
        cancel: True - if you want to cancel user creation,
                by defaul user will be created

    Throws:
        RBACOperationBlocked: If operation is blocked due to current user
            not having appropriate permissions OR update is not allowed
            for currently selected role
    """
    if self.appliance.version < "5.8":
        user_blocked_msg = "Userid has already been taken"
    else:
        user_blocked_msg = ("Userid is not unique within region {}".format(
            self.appliance.server.zone.region.number))

    user = self.instantiate(
        name=name, credential=credential, email=email, group=group)

    view = navigate_to(self, 'Add')
    view.fill({
        'name_txt': user.name,
        'userid_txt': user.credential.principal,
        'password_txt': user.credential.secret,
        'password_verify_txt': user.credential.verify_secret,
        'email_txt': user.email,
        'user_group_select': getattr(user.group, 'description', None)
    })

    if cancel:
        view.cancel_button.click()
        flash_message = 'Add of new User was cancelled by the user'
    else:
        view.add_button.click()
        flash_message = 'User "{}" was saved'.format(user.name)

    try:
        view.flash.assert_message(user_blocked_msg)
        raise RBACOperationBlocked(user_blocked_msg)
    except AssertionError:
        pass

    view = self.create_view(AllUserView)
    view.flash.assert_success_message(flash_message)
    assert view.is_displayed

    # To ensure tree update
    view.browser.refresh()
    return user


@navigator.register(UserCollection, 'All')
class UserAll(CFMENavigateStep):
    VIEW = AllUserView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Users')


@navigator.register(UserCollection, 'Add')
class UserAdd(CFMENavigateStep):
    VIEW = AddUserView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new User")


@navigator.register(User, 'Details')
class UserDetails(CFMENavigateStep):
    VIEW = DetailsUserView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Users', self.obj.name)


@navigator.register(User, 'Edit')
class UserEdit(CFMENavigateStep):
    VIEW = EditUserView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this User')


@navigator.register(User, 'EditTags')
class UserTagsEdit(CFMENavigateStep):
    VIEW = EditTagsUserView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select(
            "Edit 'My Company' Tags for this User")


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
    class my_company_tags(Tab):  # noqa
        """ Represents 'My company tags' tab in Group Form """
        TAB_NAME = "My Company Tags"
        tree_locator = 'tags_treebox'
        tree = CheckableBootstrapTreeview(tree_locator)

    @View.nested
    class hosts_and_clusters(Tab):  # noqa
        """ Represents 'Hosts and Clusters' tab in Group Form """
        TAB_NAME = "Hosts & Clusters"
        tree = CheckableBootstrapTreeview('hac_treebox')

    @View.nested
    class vms_and_templates(Tab):  # noqa
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
    toolbar = View.nested(AccessControlToolbar)

    @property
    def is_displayed(self):
        return (
            self.accordions.accesscontrol.is_opened and
            self.title.text == 'EVM Group "{}"'.format(self.context['object'].description) and
            # tree.currently_selected returns a list of strings with each item being the text of
            # each level of the accordion. Last element should be the Group's name
            (self.accordions.accesscontrol.tree.currently_selected[-1] ==
             self.context['object'].description)
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
    toolbar = View.nested(AccessControlToolbar)
    table = Table("//div[@id='main_div']//table")
    paginator = PaginationPane()

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
        '//button[@title="Move selected fields up"]/i',
        '//button[@title="Move selected fields down"]/i')

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


def _fill_ldap_group_lookup(obj, view):
    """ Fills ldap info for group lookup

    Args: view: view for group creation(AddGroupView)
    """
    view.fill({'ldap_groups_for_user': obj.description,
               'description_txt': obj.description,
               'role_select': obj.role.name,
               'group_tenant': obj.tenant})
    view.add_button.click()
    view = obj.create_view(AllGroupView)
    view.flash.assert_success_message('Group "{}" was saved'.format(obj.description))
    assert view.is_displayed


@MiqImplementationContext.external_for(Group.add_group_from_ldap_lookup, ViaUI)
def g_add_group_from_ldap_lookup(self):
    """Adds a group from ldap lookup"""
    view = navigate_to(self, 'Add')
    view.fill({'lookup_ldap_groups_chk': True,
               'user_to_look_up': self.user_to_lookup,
               'username': self.ldap_credentials.principal,
               'password': self.ldap_credentials.secret})
    view.retrieve_button.click()
    self._fill_ldap_group_lookup(self, view)


@MiqImplementationContext.external_for(Group.add_group_from_ext_auth_lookup, ViaUI)
def g_add_group_from_ext_auth_lookup(self):
    """Adds a group from external authorization lookup"""
    view = navigate_to(self, 'Add')
    view.fill({'lookup_ldap_groups_chk': True,
               'user_to_look_up': self.user_to_lookup})
    view.retrieve_button.click()
    self._fill_ldap_group_lookup(self, view)


@MiqImplementationContext.external_for(Group.update, ViaUI)
def g_update(self, updates):
    """ Update group method

    Args:
        updates: group data that should be changed

    Note: In case updates is the same as original group data, update will be canceled,
    as 'Save' button will not be active
    """
    edit_group_txt = 'Edit this Group'

    view = navigate_to(self, 'Details')
    if not view.toolbar.configuration.item_enabled(edit_group_txt):
        raise RBACOperationBlocked("Configuration action '{}' is not enabled".format(
            edit_group_txt))
    view = navigate_to(self, 'Edit')

    changed = view.fill({
        'description_txt': updates.get('description'),
        'role_select': updates.get('role').name,
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


@MiqImplementationContext.external_for(Group.delete, ViaUI)
def g_delete(self, cancel=True):
    """
    Delete existing group

    Args:
        cancel: Default value 'True', group will be deleted
                'False' - deletion of group will be canceled
    Throws:
        RBACOperationBlocked: If operation is blocked due to current user
            not having appropriate permissions OR delete is not allowed
            for currently selected group
    """
    flash_success_msg = 'EVM Group "{}": Delete successful'.format(self.description)
    flash_blocked_msg_list = [
        ('EVM Group "{}": '
         'Error during delete: A read only group cannot be deleted.'.format(self.description)),
        ('EVM Group "{}": Error during delete: '
         'The group has users assigned that do not '
         'belong to any other group'.format(self.description))]
    delete_group_txt = 'Delete this Group'

    view = navigate_to(self, 'Details')

    if not view.toolbar.configuration.item_enabled(delete_group_txt):
        raise RBACOperationBlocked("Configuration action '{}' is not enabled".format(
            delete_group_txt))

    view.toolbar.configuration.item_select(delete_group_txt, handle_alert=cancel)
    for flash_blocked_msg in flash_blocked_msg_list:
        try:
            view.flash.assert_message(flash_blocked_msg)
            raise RBACOperationBlocked(flash_blocked_msg)
        except AssertionError:
            pass

    view.flash.assert_no_error()
    view.flash.assert_message(flash_success_msg)

    if cancel:
        view = self.create_view(AllGroupView)
        view.flash.assert_success_message(flash_success_msg)
    else:
        view = self.create_view(DetailsGroupView)
        assert view.is_displayed, (
            "Access Control Group {} Detail View is not displayed".format(self.description))


@MiqImplementationContext.external_for(Group.edit_tags, ViaUI)
def g_edit_tags(self, tag, value):
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


@MiqImplementationContext.external_for(Group.remove_tag, ViaUI)
def g_remove_tag(self, tag, value):
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


@MiqImplementationContext.external_for(Group.get_tags, ViaUI)
def g_get_tags(self):
    tags = []
    view = navigate_to(self, 'EditTags')
    for row in view.tag_table:
        tags.append((row.category.text, row.assigned_value.text))
    view.cancel_button.click()
    return tags


@MiqImplementationContext.external_for(Group.set_group_order, ViaUI)
def g_set_group_order(self, updated_order):
    """ Sets group order for group lookup

    Args:
        updated_order: group order list
    """
    name_column = "Name"
    find_row_kwargs = {name_column: self.description}
    view = navigate_to(self.parent, 'All')
    row = view.paginator.find_row_on_pages(view.table, **find_row_kwargs)
    original_sequence = row.sequence.text

    original_order = self.group_order[:len(updated_order)]
    view = self.create_view(EditGroupSequenceView)
    assert view.is_displayed

    # We pick only the same amount of items for comparing
    if updated_order == original_order:
        return  # Ignore that, would cause error on Save click
    view.group_order_selector.fill(updated_order)
    view.save_button.click()

    view = self.create_view(AllGroupView)
    assert view.is_displayed

    row = view.paginator.find_row_on_pages(view.table, **find_row_kwargs)
    changed_sequence = row.sequence.text
    assert original_sequence != changed_sequence, "{} Group Edit Sequence Failed".format(
        self.description)


def _set_group_restriction(tab_view, item, update=False):
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


@MiqImplementationContext.external_for(GroupCollection.create, ViaUI)
def gc_create(self, description=None, role=None, tenant="My Company", ldap_credentials=None,
           user_to_lookup=None, tag=None, host_cluster=None, vm_template=None, cancel=False):
    """ Create group method

    Args:
        description: group description
        role: group role
        tenant: group tenant
        user_to_lookup: ldap user to lookup
        ldap_credentials: ldap user credentials
        tag: tag for group restriction
        host_cluster: host/cluster for group restriction
        vm_template: vm/template for group restriction
        cancel: True - if you want to cancel group creation,
                by default group will be created
    Throws:
        RBACOperationBlocked: If operation is blocked due to current user
            not having appropriate permissions OR delete is not allowed
            for currently selected user
    """
    if self.appliance.version < "5.8":
        flash_blocked_msg = ("Description has already been taken")
    else:
        flash_blocked_msg = "Description is not unique within region {}".format(
            self.appliance.server.zone.region.number)

    view = navigate_to(self, 'Add')

    group = self.instantiate(
        description=description, role=role, tenant=tenant, ldap_credentials=ldap_credentials,
        user_to_lookup=user_to_lookup, tag=tag, host_cluster=host_cluster,
        vm_template=vm_template)

    view.fill({
        'description_txt': group.description,
        'role_select': group.role.name,
        'group_tenant': group.tenant
    })

    _set_group_restriction(view.my_company_tags, group.tag)
    _set_group_restriction(view.hosts_and_clusters, group.host_cluster)
    _set_group_restriction(view.vms_and_templates, group.vm_template)

    if cancel:
        view.cancel_button.click()
        flash_message = 'Add of new Group was cancelled by the user'
    else:
        view.add_button.click()
        flash_message = 'Group "{}" was saved'.format(group.description)
    view = self.create_view(AllGroupView)

    try:
        view.flash.assert_message(flash_blocked_msg)
        raise RBACOperationBlocked(flash_blocked_msg)
    except AssertionError:
        pass

    view.flash.assert_success_message(flash_message)
    assert view.is_displayed

    # To ensure that the group list is updated
    view.browser.refresh()
    return group


@navigator.register(GroupCollection, 'All')
class GroupAll(CFMENavigateStep):
    VIEW = AllGroupView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Groups')


@navigator.register(GroupCollection, 'Add')
class GroupAdd(CFMENavigateStep):
    VIEW = AddGroupView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select("Add a new Group")


@navigator.register(Group, 'EditGroupSequence')
class EditGroupSequence(CFMENavigateStep):
    VIEW = EditGroupSequenceView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Edit Sequence of User Groups for LDAP Look Up')


@navigator.register(Group, 'Details')
class GroupDetails(CFMENavigateStep):
    VIEW = DetailsGroupView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.accordions.accesscontrol.tree.click_path(
            self.obj.appliance.server_region_string(), 'Groups', self.obj.description)


@navigator.register(Group, 'Edit')
class GroupEdit(CFMENavigateStep):
    VIEW = EditGroupView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Group')


@navigator.register(Group, 'EditTags')
class GroupTagsEdit(CFMENavigateStep):
    VIEW = GroupEditTagsView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select(
            "Edit 'My Company' Tags for this Group")
