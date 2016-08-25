from utils.pretty import Pretty

from selenium_view import View, AttributeValue, VersionPick, Text
from utils import version


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


class BasicLoggedInView(View):
    csrf_token = AttributeValue('//meta[@name="csrf-token"]', 'content')
    user_dropdown = VersionPick({
        version.LOWEST: Text('//div[@id="page_header_div"]//li[contains(@class, "dropdown")]'),
        '5.4': Text(
            '//nav//ul[contains(@class, "navbar-utility")]/li[contains(@class, "dropdown")]/a'),
        '5.6.0.1': Text('//nav//a[@id="dropdownMenu2"]'),
    })
    logout = Text('//a[contains(@href, "/logout")]')

    @property
    def is_displayed(self):
        return self.user_dropdown.is_displayed

    @property
    def logged_in(self):
        self.browser.ensure_page_safe(timeout='90s')
        return self.is_displayed

    @property
    def logged_out(self):
        return not self.logged_in
