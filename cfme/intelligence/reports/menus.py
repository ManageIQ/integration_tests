# -*- coding: utf-8 -*-
"""Module handling report menus contents"""
from contextlib import contextmanager

from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import FolderManager
from cfme.web_ui import Region, Tree, accordion, form_buttons, menu
from cfme.web_ui.multibox import MultiBoxSelect
from utils.log import logger

menu.nav.add_branch(
    "reports",
    {
        "report_menus_group":
        lambda ctx: accordion.tree("Edit Report Menus", "All EVM Groups", ctx["group"])
    }
)

reports_tree = Tree("//div[@id='menu_roles_treebox']/ul")

manager = FolderManager("//div[@id='folder_lists']/table")
report_select = MultiBoxSelect(
    "//select[@id='available_reports']",
    "//select[@id='selected_reports']",
    "//a[@title='Move selected reports right']/img",
    "//a[@title='Move selected reports left']/img",
)

buttons = Region(locators=dict(
    commit="//a[@title='Commit report management changes']/img",
    discard="//a[@title='Discard report management changes']/img",
))

default_button = form_buttons.FormButton("Reset All menus to CFME defaults")


def get_folders(group):
    """Returns list of folders for given user group.

    Args:
        group: User group to check.
    """
    sel.force_navigate("report_menus_group", context={"group": group})
    reports_tree.click_path("Top Level")
    return manager.fields


def get_subfolders(group, folder):
    """Returns list of sub-folders for given user group and folder.

    Args:
        group: User group to check.
        folder: Folder to read.
    """
    sel.force_navigate("report_menus_group", context={"group": group})
    reports_tree.click_path("Top Level", folder)
    return manager.fields


def add_folder(group, folder):
    """Adds a folder under top-level.

    Args:
        group: User group.
        folder: Name of the new folder.
    """
    with manage_folder() as top_level:
        top_level.add(folder)


def add_subfolder(group, folder, subfolder):
    """Adds a subfolder under specified folder.

    Args:
        group: User group.
        folder: Name of the folder.
        subfolder: Name of the new subdfolder.
    """
    with manage_folder(folder) as fldr:
        fldr.add(subfolder)


def reset_to_default(group):
    """Clicks the `Default` button.

    Args:
        group: Group to set to Default
    """
    sel.force_navigate("report_menus_group", context={"group": group})
    sel.click(default_button)
    sel.click(form_buttons.save)


@contextmanager
def manage_folder(group, folder=None):
    """Context manager to use when modifying the folder contents.

    You can use manager's :py:meth:`FolderManager.bail_out` classmethod to end and discard the
    changes done inside the with block. This context manager does not give the manager as a value to
    the with block so you have to import and use the :py:class:`FolderManager` class manually.

    Args:
        group: User group.
        folder: Which folder to manage. If None, top-level will be managed.
    Returns: Context-managed :py:class:`cfme.intelligence.reports.ui_elements.FolderManager` inst.
    """
    sel.force_navigate("report_menus_group", context={"group": group})
    if folder is None:
        reports_tree.click_path("Top Level")
    else:
        reports_tree.click_path("Top Level", folder)
    try:
        yield manager
    except FolderManager._BailOut:
        logger.info("Discarding editation modifications on %s", str(repr(manager)))
        manager.discard()
    except:
        # In case of any exception, nothing will be saved
        manager.discard()
        raise  # And reraise the exception
    else:
        # If no exception happens, save!
        manager.commit()
        form_buttons.save()


@contextmanager
def manage_subfolder(group, folder, subfolder):
    """Context manager to use when modifying the subfolder contents.

    You can use manager's :py:meth:`FolderManager.bail_out` classmethod to end and discard the
    changes done inside the with block.

    Args:
        group: User group.
        folder: Parent folder name.
        subfolder: Subfodler name to manage.
    Returns: Context-managed :py:class:`cfme.intelligence.reports.ui_elements.FolderManager` inst.
    """
    sel.force_navigate("report_menus_group", context={"group": group})
    reports_tree.click_path("Top Level", folder, subfolder)
    try:
        yield report_select
    except FolderManager._BailOut:
        logger.info("Discarding editation modifications on %s", str(repr(manager)))
        manager.discard()
    except:
        # In case of any exception, nothing will be saved
        manager.discard()
        raise  # And reraise the exception
    else:
        # If no exception happens, save!
        manager.commit()
        form_buttons.save()
