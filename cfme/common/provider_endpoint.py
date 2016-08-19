from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill, form_buttons


class ProviderEndpoint(object):
    def __init__(self, kwargs):
        self.values = kwargs

    def fill(self, validate=True, change_stored=False):
        if change_stored:
            sel.click('//a[contains(., "Change stored password")]')
        fill(self.form, self.values)
        fill(form_buttons.validate, validate)
