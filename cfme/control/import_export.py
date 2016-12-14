# -*- coding: utf-8 -*-
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from navmazing import NavigateToSibling

from widgetastic.widget import Select, ClickableMixin
from widgetastic_patternfly import BootstrapSelect, Button, Input

from cfme import BaseLoggedInPage
from cfme.base.ui import Server


class InputButton(Input, ClickableMixin):
    pass


class ControlImportExportView(BaseLoggedInPage):

    upload_button = InputButton("commit")
    export_button = Button("Export")
    commit_button = Button("Commit")

    upload_file = Input("upload[file]")
    export = BootstrapSelect("dbtype")
    policy_profiles = Select(id="choices_chosen_")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Control", "Import / Export"]
        )


@navigator.register(Server)
class ControlImportExport(CFMENavigateStep):
    VIEW = ControlImportExportView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Control", "Import / Export")


def import_file(filename, cancel=False):
    """ Go to Control / Import Export and import given file.

    Args:
        filename: Full path to file to import.
        cancel: Whether to click Cancel instead of commit.
    """
    view = navigate_to(Server, "ControlImportExport")
    assert view.is_displayed
    view.fill({
        "upload_file": filename
    })
    if cancel:
        view.cancel_button.click()
    else:
        view.upload_button.click()
    view.flash.assert_no_error()
    view.flash.assert_message("Press commit to Import")
    view.commit_button.click()


def is_imported(policy_profile):
    view = navigate_to(Server, "ControlImportExport")
    assert view.is_displayed
    return policy_profile in view.policy_profiles.read()
