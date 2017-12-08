# -*- coding: utf-8 -*-
"""Module handling report menus contents"""
from contextlib import contextmanager
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from widgetastic.widget import Text
from widgetastic_manageiq import ManageIQTree, FolderManager
from widgetastic_patternfly import Button
from navmazing import NavigateToAttribute

from . import CloudIntelReportsView, ReportsMultiBoxSelect


class EditReportMenusView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    reports_tree = ManageIQTree("menu_roles_treebox")
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


class ReportMenu(Navigatable):
    """
        This is a fake class mainly needed for navmazing navigation.

    """
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)
        self.group = None

    def go_to_group(self, group_name):
        self.group = group_name
        view = navigate_to(self, "EditReportMenus")
        assert view.is_displayed
        return view

    def get_folders(self, group):
        """Returns list of folders for given user group.

        Args:
            group: User group to check.
        """
        view = self.go_to_group(group)
        view.reports_tree.click_path("Top Level")
        return view.manager.fields

    def get_subfolders(self, group, folder):
        """Returns list of sub-folders for given user group and folder.

        Args:
            group: User group to check.
            folder: Folder to read.
        """
        view = self.go_to_group(group)
        view.reports_tree.click_path("Top Level", folder)
        return view.manager.fields

    def add_folder(self, group, folder):
        """Adds a folder under top-level.

        Args:
            group: User group.
            folder: Name of the new folder.
        """
        with self.manage_folder() as top_level:
            top_level.add(folder)

    def add_subfolder(self, group, folder, subfolder):
        """Adds a subfolder under specified folder.

        Args:
            group: User group.
            folder: Name of the folder.
            subfolder: Name of the new subdfolder.
        """
        with self.manage_folder(folder) as fldr:
            fldr.add(subfolder)

    def reset_to_default(self, group):
        """Clicks the `Default` button.

        Args:
            group: Group to set to Default
        """
        view = self.go_to_group(group)
        view.default_button.click()
        view.save_button.click()

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


@navigator.register(ReportMenu)
class EditReportMenus(CFMENavigateStep):
    VIEW = EditReportMenusView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.view.edit_report_menus.tree.click_path(
            "All EVM Groups",
            self.obj.group
        )
