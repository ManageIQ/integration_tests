from utils.pretty import Pretty

from widgetastic.widget import View
from widgetastic_patternfly import NavDropdown, VerticalNavigation, FlashMessages


class Credential(Pretty):
    """
    A class to fill in credentials

    Args:
        principal: Something
        secret: Something
        verify_secret: Something
    """
    pretty_attrs = ['principal', 'secret']

    def __init__(self, principal=None, secret=None, verify_secret=None, **ignore):
        self.principal = principal
        self.secret = secret
        self.verify_secret = verify_secret

    def __getattribute__(self, attr):
        if attr == 'verify_secret':
            vs = object.__getattribute__(self, 'verify_secret')
            if vs is None:
                return object.__getattribute__(self, 'secret')
            else:
                return vs
        elif attr == "verify_token":
            try:
                vs = object.__getattribute__(self, 'verify_token')
            except AttributeError:
                return object.__getattribute__(self, 'token')
        else:
            return object.__getattribute__(self, attr)


class BaseLoggedInPage(View):
    """This page should be subclassed by any page that models any other page that is available as
    logged in.
    """
    flash = FlashMessages('div#flash_text_div')
    help = NavDropdown('.//li[./a[@id="dropdownMenu1"]]')
    settings = NavDropdown('.//li[./a[@id="dropdownMenu2"]]')
    navigation = VerticalNavigation('#maintab')

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user

    def logged_in_as_user(self, user):
        if self.logged_out:
            return False

        return user.full_name == self.current_fullname

    @property
    def logged_in_as_current_user(self):
        return self.logged_in_as_user(self.extra.store.user)

    @property
    def current_username(self):
        try:
            return self.extra.store.user.principal
        except AttributeError:
            return None

    @property
    def current_fullname(self):
        return self.settings.text.strip().split('|', 1)[0].strip()

    @property
    def logged_in(self):
        return self.settings.is_displayed

    @property
    def logged_out(self):
        return not self.logged_in

    def logout(self):
        self.settings.select_item('Logout')
        self.browser.handle_alert(wait=None)
        self.extra.store.user = None
