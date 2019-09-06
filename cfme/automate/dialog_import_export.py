from navmazing import NavigateToAttribute
from widgetastic.widget import Checkbox
from widgetastic.widget import FileInput
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import Updateable


class DialogImportExportView(BaseLoggedInPage):
    """ Dialog Import Export file view"""

    title = Text("#explorer_title_text")
    upload_file = FileInput(id="upload_file")
    upload = Button(id="upload_service_dialog_import")

    def in_import_export(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ["Automation", "Automate", "Customization"]
            and self.title.text == "Service Dialog Import / Export"
        )

    @property
    def is_displayed(self):
        return (
            self.in_import_export
            and self.upload.is_displayed
        )

    @View.nested
    class fileimport(View):  # noqa
        """File select view"""

        select_dialog = Checkbox(id="check-all")
        commit = Button(name="commit")

        @property
        def is_displayed(self):
            return (
                self.in_import_export and
                self.select_dialog.is_displayed and
                self.commit.is_displayed
            )


class DialogImportExport(Updateable, NavigatableMixin):
    """Dialog Import Export"""

    def __init__(self, appliance):
        self.appliance = appliance

    def import_dialog(self, file_path):
        """ Import dialog by uploading yml
        Args:
            file_path: file path
        """
        view = navigate_to(self, "DialogImportExport")
        view.upload_file.fill(file_path)
        view.upload.click()
        view.fileimport.select_dialog.click()
        view.fileimport.commit.click()
        view.flash.assert_success_message('Service dialogs imported successfully')
        # TODO - add method for exporting dialog


@navigator.register(DialogImportExport, "DialogImportExport")
class DialogImportExportPage(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "AutomateCustomization")
    VIEW = DialogImportExportView

    def step(self):
        self.prerequisite_view.import_export.tree.click_path('Service Dialog Import/Export')
