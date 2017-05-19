# -*- coding: utf-8 -*-
"""Page model for Automation/Anisble/Repositories"""
from navmazing import NavigateToAttribute, NavigateToSibling, NavigationDestinationNotFound

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from widgetastic.widget import Text, Checkbox
from widgetastic_manageiq import Table
from widgetastic_patternfly import Dropdown, Button, Input, FlashMessages
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.wait import wait_for


class RepositoryBaseView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@class, "flash_text_div") or @id="flash_text_div"]')
    title = Text(locator=".//h1")

    @property
    def in_ansible_repositories(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Ansible", "Repositories"]
        )


class RepositoryListView(RepositoryBaseView):
    configuration = Dropdown("Configuration")
    repositories = Table(".//div[@id='list_grid']/table")

    @property
    def is_displayed(self):
        return self.in_ansible_repositories and self.title.text == "Repositories"


class RepositoryDetailsView(RepositoryBaseView):
    configuration = Dropdown("Configuration")
    download = Button(title="Download summary in PDF format")

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == "{} (Summary)".format(self.context["object"].name)
        )


class RepositoryFormView(RepositoryBaseView):
    name = Input(name="name")
    description = Input(name="description")
    url = Input(name="scm_url")
    scm_credentials = Dropdown("Select credentials")
    scm_branch = Input(name="scm_branch")
    # SCM Update Options
    clean = Checkbox(name="clean")
    delete_on_update = Checkbox(name="scm_delete_on_update")
    update_on_launch = Checkbox(name="scm_update_on_launch")

    cancel_button = Button("Cancel")


class RepositoryAddView(RepositoryFormView):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == "Add new Repository"
        )


class RepositoryEditView(RepositoryFormView):
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == 'Edit Repository "{}"'.format(self.context["object"].name)
        )


class RepositoryCollection(Navigatable):
    """Collection object for the :py:class:`Repository`."""

    def create(self, name, url, description=None, scm_credentials=None, scm_branch=None,
               clean=None, delete_on_update=None, update_on_launch=None):
        add_page = navigate_to(self, "Add")
        fill_dict = {
            "name": name,
            "description": description,
            "url": url,
            "scm_credentials": scm_credentials,
            "scm_branch": scm_branch,
            "clean": clean,
            "delete_on_update": delete_on_update,
            "update_on_launch": update_on_launch
        }
        add_page.fill(fill_dict)
        add_page.add_button.click()
        repo_list_page = self.create_view(RepositoryListView)
        assert repo_list_page.is_displayed
        repo_list_page.flash.assert_no_error()
        repo_list_page.flash.assert_message(
            'Add of Repository "{}" was successfully initialized.'.format(name))

        def _wait_until_appeared():
            for row in repo_list_page.repositories:
                if row["Name"].text == name:
                    return True
            else:
                return False

        wait_for(_wait_until_appeared, delay=10, fail_func=repo_list_page.browser.selenium.refresh)
        return Repository(name, url, description=description, scm_credentials=scm_credentials,
            scm_branch=scm_branch, clean=clean, delete_on_update=delete_on_update,
            update_on_launch=update_on_launch, appliance=self.appliance)


class Repository(Navigatable):
    """A class representing one Embedded Ansible repository in the UI."""
    def __init__(self, name, url, description=None, scm_credentials=None, scm_branch=None,
            clean=None, delete_on_update=None, update_on_launch=None, collection=None,
            appliance=None):
        if collection is None:
            collection = RepositoryCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=collection.appliance)
        self.name = name
        self.url = url
        self.description = description
        self.scm_credentials = scm_credentials
        self.scm_branch = scm_branch
        self.clean = clean
        self.delete_on_update = delete_on_update
        self.update_on_launch = update_on_launch

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(RepositoryListView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Edit of Repository "{}" was successfully initialized.'.format(
                    updates.get("name", self.name)))
        else:
            view.flash.assert_message(
                'Edit of Repository "{}" cancelled by the user.'.format(self.name))

    def delete(self):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove this Repository", handle_alert=True)
        repo_list_page = self.create_view(RepositoryListView)
        assert repo_list_page.is_displayed
        repo_list_page.flash.assert_no_error()
        repo_list_page.flash.assert_message(
            'Delete of Repository "{}" was successfully initiated.'.format(self.name))

        def _wait_until_removed():
            for row in repo_list_page.repositories:
                if row["Name"].text == self.name:
                    return False
            else:
                return True

        wait_for(_wait_until_removed, delay=10, fail_func=repo_list_page.browser.selenium.refresh)

    def refresh(self):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Refresh this Repository", handle_alert=True)
        view.flash.assert_no_error()
        view.flash.assert_message("Embedded Ansible refresh has been successfully initiated")


@navigator.register(Server)
class AnsibleRepositories(CFMENavigateStep):
    VIEW = RepositoryListView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Automation", "Ansible", "Repositories")


@navigator.register(Repository)
class Details(CFMENavigateStep):
    VIEW = RepositoryDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "AnsibleRepositories")

    def step(self):
        repositories = self.prerequisite_view.repositories
        for row in repositories:
            if row["Name"].text == self.obj.name:
                row["Name"].click()
                break
        else:
            raise NavigationDestinationNotFound(self.obj.name, "Repository", repositories)


@navigator.register(RepositoryCollection)
class Add(CFMENavigateStep):
    VIEW = RepositoryAddView
    prerequisite = NavigateToAttribute("appliance.server", "AnsibleRepositories")

    def step(self):
        self.prerequisite_view.configuration.item_select("Add New Repository")


@navigator.register(Repository)
class Edit(CFMENavigateStep):
    VIEW = RepositoryEditView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Repository")
