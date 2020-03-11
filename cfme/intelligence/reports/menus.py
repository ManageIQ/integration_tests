"""Module handling report menus contents"""
from contextlib import contextmanager

import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic_patternfly import Button

from cfme.intelligence.reports import CloudIntelReportsView
from cfme.intelligence.reports import ReportsMultiBoxSelect
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import FolderManager
from widgetastic_manageiq import ManageIQTree


class AllReportMenusView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    reports_tree = ManageIQTree("menu_roles_treebox")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports
            and self.title.text == "All EVM Groups"
            and self.edit_report_menus.is_opened
            and self.edit_report_menus.tree.currently_selected == ["All EVM Groups"]
        )


class EditReportMenusView(AllReportMenusView):
    # Buttons
    save_button = Button("Save")
    reset_button = Button("Reset")
    default_button = Button("Default")
    cancel_button = Button("Cancel")
    commit_button = Button("Commit")
    discard_button = Button("Discard")

    manager = FolderManager(".//div[@id='folder_lists']/table")
    report_select = ReportsMultiBoxSelect(
        move_into="Move selected reports right",
        move_from="Move selected reports left",
        available_items="available_reports",
        chosen_items="selected_reports"
    )

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Editing EVM Group "{}"'.format(self.context["object"].group) and
            self.edit_report_menus.is_opened and
            self.edit_report_menus.tree.currently_selected == [
                "All EVM Groups",
                self.context["object"].group
            ]
        )


@attr.s
class ReportMenu(BaseEntity):
    """
        This is a fake class mainly needed for navmazing navigation.

    """
    group = None

    def go_to_group(self, group_name):
        self.group = group_name
        view = navigate_to(self, "Edit")
        assert view.is_displayed
        return view

    def get_folders(self, group):
        """Returns list of folders for given user group.

        Args:
            group: User group to check.
        """
        view = self.go_to_group(group)
        view.reports_tree.click_path("Top Level")
        fields = view.manager.fields
        view.discard_button.click()
        return fields

    def get_subfolders(self, group, folder):
        """Returns list of sub-folders for given user group and folder.

        Args:
            group: User group to check.
            folder: Folder to read.
        """
        view = self.go_to_group(group)
        view.reports_tree.click_path("Top Level", folder)
        fields = view.manager.fields
        view.discard_button.click()
        return fields

    def _action(self, action, manager, folder_name):
        with manager as folder_manager:
            getattr(folder_manager, action)(folder_name)

    def add_folder(self, group, folder):
        """Adds a folder under top-level.

        Args:
            group: User group.
            folder: Name of the new folder.
        """
        self._action("add", self.manage_folder(group), folder)

    def add_subfolder(self, group, folder, subfolder):
        """Adds a subfolder under specified folder.

        Args:
            group: User group.
            folder: Name of the folder.
            subfolder: Name of the new subfolder.
        """
        self._action("add", self.manage_folder(group, folder), subfolder)

    def remove_folder(self, group, folder):
        """Removes a folder under top-level.

        Args:
            group: User group.
            folder: Name of the folder.
        """
        self._action("delete", self.manage_folder(group), folder)

    def remove_subfolder(self, group, folder, subfolder):
        """Removes a subfolder under specified folder.

        Args:
            group: User group.
            folder: Name of the folder.
            subfolder: Name of the subfolder.
        """
        self._action("delete", self.manage_folder(group, folder), subfolder)

    def reset_to_default(self, group):
        """Clicks the `Default` button.

        Args:
            group: Group to set to Default
        """
        view = self.go_to_group(group)
        view.default_button.click()
        view.save_button.click()
        flash_view = self.create_view(AllReportMenusView)
        flash_view.flash.assert_message(
            'Report Menu for role "{}" was saved'.format(group)
        )

    @contextmanager
    def manage_subfolder(self, group, folder, subfolder):
        """Context manager to use when modifying the subfolder contents.

        You can use manager's :py:meth:`FolderManager.bail_out` classmethod to end and discard the
        changes done inside the with block.

        Args:
            group: User group.
            folder: Parent folder name.
            subfolder: Subfolder name to manage.
        Returns: Context-managed :py:class: `widgetastic_manageiq.MultiBoxSelect` instance
        """
        view = self.go_to_group(group)
        view.reports_tree.click_path("Top Level", folder, subfolder)
        try:
            yield view.report_select
        except FolderManager._BailOut:
            view.discard_button.click()
        except Exception:
            # In case of any exception, nothing will be saved
            view.discard_button.click()
            raise  # And reraise the exception
        else:
            # If no exception happens, save!
            view.commit_button.click()
            view.save_button.click()
            flash_view = self.create_view(AllReportMenusView)
            flash_view.flash.assert_message(
                'Report Menu for role "{}" was saved'.format(group)
            )

    @contextmanager
    def manage_folder(self, group, folder=None):
        """Context manager to use when modifying the folder contents.

        You can use manager's :py:meth:`FolderManager.bail_out` classmethod to end and discard the
        changes done inside the with block. This context manager does not give the manager as a
        value to the with block so you have to import and use the :py:class:`FolderManager` class
        manually.

        Args:
            group: User group.
            folder: Which folder to manage. If None, top-level will be managed.
        Returns: Context-managed :py:class:`widgetastic_manageiq.FolderManager` instance
        """
        view = self.go_to_group(group)
        if folder is None:
            view.reports_tree.click_path("Top Level")
        else:
            view.reports_tree.click_path("Top Level", folder)
        try:
            yield view.manager
        except FolderManager._BailOut:
            view.manager.discard()
        except Exception:
            # In case of any exception, nothing will be saved
            view.manager.discard()
            raise  # And reraise the exception
        else:
            # If no exception happens, save!
            view.manager.commit()
            view.save_button.click()
            flash_view = self.create_view(AllReportMenusView)
            flash_view.flash.assert_message(
                'Report Menu for role "{}" was saved'.format(group)
            )

    def move_reports(self, group, folder, subfolder, *reports):
        """ Moves a list of reports to a given menu
        Args:
            group: User group
            folder: Parent of the subfolder where reports are to be moved.
            subfolder: Subfolder under which the reports are to be moved.
            reports: List of reports that are to be moved.
        """
        reports = list(reports)
        cancel_view = ""

        with self.manage_subfolder(group, folder, subfolder) as selected_menu:
            selected_options = selected_menu.parent_view.report_select.all_options

            diff = set(selected_options) & set(reports)
            if diff and (len(diff) == len(reports)):
                cancel_view = self.create_view(AllReportMenusView)
                # If all the reports to be moved are already present, raise an exception to exit.
                raise FolderManager._BailOut

            # fill method replaces all the options in all_options with the value passed as argument
            # We do not want to replace any value, we just want to move the new reports to a given
            # menu. This is a work-around for that purpose.
            reports.extend(selected_options)
            selected_menu.parent_view.report_select.fill(reports)

        if cancel_view:
            cancel_view.flash.assert_message(
                'Edit of Report Menu for role "{}" was cancelled by the user'.format(
                    group
                )
            )


@attr.s
class ReportMenusCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.intelligence.reports.ReportMenu'."""

    ENTITY = ReportMenu


@navigator.register(ReportMenu, "Edit")
class EditReportMenus(CFMENavigateStep):
    VIEW = EditReportMenusView
    prerequisite = NavigateToAttribute(
        "appliance.collections.intel_report_menus", "All"
    )

    def step(self, *args, **kwargs):
        self.prerequisite_view.edit_report_menus.tree.click_path(
            "All EVM Groups", self.obj.group
        )


@navigator.register(ReportMenusCollection, "All")
class ReportMenus(CFMENavigateStep):
    VIEW = AllReportMenusView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.edit_report_menus.tree.click_path("All EVM Groups")
