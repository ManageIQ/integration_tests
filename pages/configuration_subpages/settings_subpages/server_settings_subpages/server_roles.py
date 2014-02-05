import re
from utils.conf import cfme_data
from utils.log import logger
from selenium.webdriver.common.by import By


class ServerRoleList:

    _server_roles_selector = (By.CSS_SELECTOR, ".col2 > dd > fieldset:nth-child(2) \
            input[name*='server_roles']")

    @property
    def _server_role_elements(self):
        return self.selenium.find_elements(*self._server_roles_selector)

    @property
    def server_roles(self):
        return [ServerRole(el) for el in self._server_role_elements]

    @property
    def selected_server_role_names(self):
        role_names = list()
        for role in self.server_roles:
            if role.is_selected:
                role_names.append(role.name)
        return role_names

    def _select_server_role(self, role_name):
        for role in self.server_roles:
            if role.name == role_name:
                role.select()

    def _unselect_server_role(self, role_name):
        for role in self.server_roles:
            if role.name == role_name:
                role.unselect()

    def default_server_roles_list(self):
        """ Get the default appliance roles stored in cfme_data.yaml that can be then passed to
        set_server_roles.

        Returns:
            A list of the default appliance roles
        """
        return cfme_data["server_roles"]["default"][:]

    def ui_only_role_list(self):
        """ Single UI interface role which can be used to flush all the server roles but that one
        when passed to set_server_roles.

        Returns:
            A list of the single UI interface role
        """
        return ["user_interface"]

    def get_all_role_list(self):
        """ Get the current configured server roles

        Returns:
            List of current configured roles.
        """
        all_roles = self.server_roles
        role_changes = []
        for role in all_roles:
            role_changes.append("+" + str(role.name))
        return role_changes

    def edit_current_role_list(self, role_changes):
        """ Updates the current configured roles with desired changes.

        Args:
            role_changes: A String containing space seperated roles to change.

                If prefixed with + or nothing, it adds,
                if prefixed with -, it removes the role. It can be combined either
                in string and in list, so these lines are functionally equivalent:

                "+automate -foo bar" # (add automate and bar, remove foo)

        Returns:
            Nothing.  Just makes the changes to the appliance.

        """
        selected_roles = self.selected_server_role_names
        self.set_server_roles(self._create_role_list(selected_roles, role_changes))

    def edit_defaults_list(self, role_changes):
        """ Updates the current configured roles with desired changes.

        Args:
            A String containing space seperated roles to change.

                If prefixed with + or nothing, it adds,
                if prefixed with -, it removes the role. It can be combined either
                in string and in list, so these lines are functionally equivalent:

                "+automate -foo bar" # (add automate and bar, remove foo)

        Returns:
            Nothing.  Just makes the changes to the appliance.

        """
        starting_list = self.default_server_roles_list()
        self.set_server_roles(self._create_role_list(starting_list, role_changes))

    def _create_role_list(self, starting_list, role_changes):
            """ Helper function to take changes and combine them with a starting list  """
            # Break the string down to the list
            if isinstance(role_changes, str):
                role_changes = [item.strip()
                    for item
                    in re.split(r"\s+", role_changes.strip())
                    if len(item) > 0]   # Eliminate multiple spaces
            if role_changes is not None:
                # Process the prefixes to determine whether add or remove
                # Resulting format [(remove?, "role"), ...]
                if " " in role_changes and not isinstance(role_changes, list):
                    role_changes = role_changes[0].split(" ")
                elif isinstance(role_changes, str):
                    role_changes = [role_changes]
                role_changes = [(item[0] == "-",                   # 1) Bool whether remove?
                    item[1:]                          # 2) Removing the prefix +,-
                    if item.startswith(("+", "-"))    # 2) If present
                    else item)                        # 2) Else not
                    for item
                    in role_changes
                    if len(item) > 0]                  # Ensure it is not empty
                for remove, role in role_changes:
                    if remove and role in starting_list:
                        starting_list.remove(role)
                    elif not remove and role not in starting_list:
                        starting_list.append(role)
                return starting_list
            else:
                raise RoleChangesRequired('Role changes is empty')

    def set_server_roles(self, desired_roles):
        """Set the server roles based on a list of roles passed in.

        Note: Only the roles passed in will be enabled upon exit.

        List of server role names currently exposed in the CFME interface:
            - automate
            - ems_metrics_coordinator
            - ems_metrics_collector
            - ems_metrics_processor
            - database_operations
            - database_synchronization
            - event
            - ems_inventory
            - ems_operations
            - notifier
            - reporting
            - scheduler
            - rhn_mirror
            - smartproxy
            - smartstate
            - user_interface
            - web_services

        Args:
            desired_roles: A list of roles that should be enabled for the appliance.

        Raises:
            UserInterfaceRoleRequired: User interface has to be enabled for automation
            NoSuchRole: If invalid role is passed in this is thrown
        """

        # Deselecting the user interface role is really un-fun, and is
        # counterproductive in the middle of user interface testing.
        if 'user_interface' not in desired_roles:
            raise UserInterfaceRoleRequired('Refusing to remove the user_interface role')

        # Check whether we specified correct roles
        # Copy it to prevent excessive selenium querying
        # and we need also only the names
        possible_roles = [item.name for item in self.server_roles]
        for role in desired_roles:
            if role not in possible_roles:
                raise NoSuchRole("Role '%s' does not exist!" % role)

        # Set the roles!
        if sorted(self.selected_server_role_names) != sorted(desired_roles):
            for role in self.server_roles:
                if role.name in desired_roles:
                    role.select()
                else:
                    role.unselect()
            self.save()
            self._wait_for_results_refresh()
            logger.info('[server_roles]: changed to ' + str(sorted(desired_roles)))
        else:
            logger.info('[server_roles]: Server roles already match configured desired roles,' +
                ' not changing server roles')

        # If this assert fails, check roles names for typos or other minor differences
        assert sorted(self.selected_server_role_names) == sorted(desired_roles)


class ServerRole:
    def __init__(self, element):
        self.element = element

    def select(self):
        if not self.is_selected:
            self.element.click()

    def unselect(self):
        if self.is_selected:
            self.element.click()

    @property
    def name(self):
        # The 'server_roles_' prefix isn't part of the actual role name,
        # it's only part of this page's implementation, so strip it off
        return self.element.get_attribute('name').replace('server_roles_', '', 1)

    @property
    def is_selected(self):
        return self.element.is_selected()


class NoSuchRole(Exception):
    pass


class UserInterfaceRoleRequired(Exception):
    pass


class RoleChangesRequired(Exception):
    pass
