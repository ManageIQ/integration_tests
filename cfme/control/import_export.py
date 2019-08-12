# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.widget import FileInput
from widgetastic.widget import Select
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button

from cfme.base.ui import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import InputButton


class ControlImportExportView(BaseLoggedInPage):

    upload_button = InputButton("commit")
    export_button = Button("Export")
    commit_button = Button("Commit")

    upload_file = FileInput(name="upload[file]")
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

    def step(self, *args, **kwargs):
        self.view.navigation.select("Control", "Import / Export")


# TODO: This function should be on a class somewhere
def import_file(appliance, filename, cancel=False):
    """ Go to Control / Import Export and import given file.

    Args:
        filename: Full path to file to import.
        cancel: Whether to click Cancel instead of commit.
    """
    view = navigate_to(appliance.server, "ControlImportExport")
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


# TODO: This function should be on a class somewhere
def is_imported(appliance, policy_profile):
    view = navigate_to(appliance.server, "ControlImportExport")
    assert view.is_displayed
    return policy_profile in view.policy_profiles.read()
