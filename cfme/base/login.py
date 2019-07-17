from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import FlashMessages
from widgetastic_patternfly import NavDropdown
from widgetastic_patternfly import VerticalNavigation

from cfme.exceptions import CFMEException
from widgetastic_manageiq import SettingsNavDropdown


class BaseLoggedInPage(View):
    """This page should be subclassed by any page that models any other page that is available as
    logged in.
    """
    CSRF_TOKEN = '//meta[@name="csrf-token"]'
    flash = FlashMessages('.//div[@id="flash_msg_div"]')
    # TODO don't use `help` here, its a built-in
    help = NavDropdown(id="help-menu")
    configuration_settings = Text('//li[.//a[@title="Configuration"]]')  # 5.11+
    settings = SettingsNavDropdown(id="dropdownMenu2")
    navigation = VerticalNavigation('#maintab')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user

    def logged_in_as_user(self, user):
        if self.logged_out:
            return False

        return user.name == self.current_fullname

    def change_group(self, group_name):
        """ From the settings menu change to the group specified by 'group_name'
            Only available in versions >= 5.9

            User is required to be currently logged in
        """
        if not self.logged_in_as_user:
            raise CFMEException("Unable to change group when a user is not logged in")

        if group_name not in self.group_names:
            raise CFMEException("{} is not an assigned group for {}".format(
                group_name, self.current_username))

        self.settings.groups.select_item(group_name)

        return True

    @property
    def logged_in_as_current_user(self):
        return self.logged_in_as_user(self.extra.appliance.user)

    # TODO remove this property, it is erroneous. View properties should be returning data from UI
    @property
    def current_username(self):
        try:
            return self.extra.appliance.user.principal
        except AttributeError:
            return None

    @property
    def current_fullname(self):
        try:
            # When the view isn't displayed self.settings.text is None, resulting in AttributeError
            return self.settings.text.strip().split('|', 1)[0].strip()
        except AttributeError:
            return None

    @property
    def current_groupname(self):
        current_groups = self.settings.groups.items

        # User is only assigned to one group
        if len(current_groups) == 1:
            return current_groups[0]

        for group in current_groups:
            if self.settings.groups.SELECTED_GROUP_MARKER in group:
                return group.replace(self.settings.groups.SELECTED_GROUP_MARKER, '')
        else:
            # Handle some weird case where we don't detect a current group
            raise CFMEException("User is not currently assigned to a group")

    @property
    def group_names(self):
        """ Return a list of the logged in user's assigned groups.

        Returns:
            list containing all groups the logged in user is assigned to
        """

        return [
            group.replace(self.settings.groups.SELECTED_GROUP_MARKER, '')
            for group in self.settings.groups.items]

    @property
    def logged_in(self):
        return self.settings.is_displayed

    @property
    def logged_out(self):
        return not self.logged_in

    def logout(self):
        self.settings.select_item('Logout')
        self.browser.handle_alert(wait=None)
        self.extra.appliance.user = None

    @property
    def csrf_token(self):
        return self.browser.get_attribute('content', self.CSRF_TOKEN)

    @csrf_token.setter
    def csrf_token(self, value):
        self.browser.set_attribute('content', value, self.CSRF_TOKEN)

    @property
    def unexpected_error(self):
        if not self.browser.elements('//h1[contains(., "Unexpected error encountered")]'):
            return None
        try:
            err_el = self.browser.element('//h2[contains(., "Error text:")]/following-sibling::h3')
            return self.browser.text(err_el)
        except NoSuchElementException:
            return None
