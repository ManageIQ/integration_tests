# -*- coding: utf-8 -*-
"""Page model for Automation/Ansible/Repositories"""
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Checkbox

from cfme.base import Server
from cfme.exceptions import ItemNotFound
from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import Table, PaginationPane
from widgetastic_patternfly import Dropdown, Button, Input, FlashMessages
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.wait import wait_for
from .playbooks import PlaybooksCollection


class RepositoryBaseView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@class, "flash_text_div") or @id="flash_text_div"]')
    title = Text(locator='.//div[@id="main-content"]//h1')

    @property
    def in_ansible_repositories(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Ansible", "Repositories"]
        )


class RepositoryListView(RepositoryBaseView):
    configuration = Dropdown("Configuration")
    repositories = Table(".//div[@id='list_grid']/table")
    pagination_pane = PaginationPane()

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
    """Collection object for the :py:class:`cfme.ansible.repositories.Repository`."""

    def instantiate(self, name, url, description=None, scm_credentials=None, scm_branch=None,
           clean=None, delete_on_update=None, update_on_launch=None):
        return Repository(
            name,
            url,
            description=description,
            scm_credentials=scm_credentials,
            scm_branch=scm_branch,
            clean=clean,
            delete_on_update=delete_on_update,
            update_on_launch=update_on_launch,
            collection=self
        )

    def create(self, name, url, description=None, scm_credentials=None, scm_branch=None,
               clean=None, delete_on_update=None, update_on_launch=None):
        """Add an ansible repository in the UI and return a Repository object.

        Args:
            name (str): name of the repository
            url (str): url of the repository
            description (str): description of the repository
            scm_credentials (str): credentials of the repository
            scm_branch (str): branch name
            clean (bool): clean
            delete_on_update (bool): delete the repo at each update
            update_on_launch (bool): update the repo at each launch

        Returns: an instance of :py:class:`cfme.ansible.repositories.Repository`
        """
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
        return self.instantiate(
            name,
            url,
            description=description,
            scm_credentials=scm_credentials,
            scm_branch=scm_branch,
            clean=clean,
            delete_on_update=delete_on_update,
            update_on_launch=update_on_launch
        )

    def all(self):
        """Return all repositories of the appliance.

        Returns: a :py:class:`list` of :py:class:`cfme.ansible.repositories.Repository` instances
        """
        table = self.appliance.db.client["configuration_script_sources"]
        result = []
        for row in self.appliance.db.client.session.query(table):
            result.append(
                Repository(
                    row.name,
                    row.scm_url,
                    description=row.description,
                    scm_branch=row.scm_branch,
                    clean=row.scm_clean,
                    delete_on_update=row.scm_delete_on_update,
                    update_on_launch=row.scm_update_on_launch,
                    appliance=self.appliance
                )
            )
        return result

    def delete(self, *repositories):
        """Delete one or more ansible repositories in the UI.

        Args:
            *repositories: a list of :py:class:`cfme.ansible.repositories.Repository`
            instances to delete

        Raises:
            ValueError: if some of the repositories were not found in the UI
        """
        repositories = list(repositories)
        checked_repositories = []
        all_page = navigate_to(Server, "AnsibleRepositories")
        all_page.pagination_pane.uncheck_all()
        if not all_page.repositories.is_displayed:
            raise ValueError("No repository found!")
        for row in all_page.repositories:
            for repository in repositories:
                if repository.name == row.name.text:
                    checked_repositories.append(repository)
                    row[0].check()
                    break
            if set(repositories) == set(checked_repositories):
                break
        if set(repositories) != set(checked_repositories):
            raise ValueError("Some of the repositories were not found in the UI.")
        all_page.configuration.item_select("Remove selected Repositories", handle_alert=True)
        all_page.flash.assert_no_error()
        for repository in checked_repositories:
            all_page.flash.assert_message(
                'Delete of Repository "{}" was successfully initiated.'.format(repository.name))


class Repository(Navigatable):
    """A class representing one Embedded Ansible repository in the UI."""

    def __init__(self, name, url, description=None, scm_credentials=None, scm_branch=None,
            clean=None, delete_on_update=None, update_on_launch=None, collection=None,
            appliance=None):
        self.collection = collection or RepositoryCollection(appliance=appliance)
        Navigatable.__init__(self, appliance=self.collection.appliance)
        self.name = name
        self.url = url
        self.description = description or ""
        self.scm_credentials = scm_credentials
        self.scm_branch = scm_branch or ""
        self.clean = clean or False
        self.delete_on_update = delete_on_update or False
        self.update_on_launch = update_on_launch or False

    @property
    def db_object(self):
        table = self.appliance.db.client["configuration_script_sources"]
        return self.appliance.db.client.sessionmaker(autocommit=True).query(table).filter(
            table.name == self.name).first()

    def update(self, updates):
        """Update the repository in the UI.

        Args:
            updates (dict): :py:class:`dict` of the updates.
        """
        original_updated_at = self.db_object.updated_at
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

            def _wait_until_changes_applied():
                changed_updated_at = self.db_object.updated_at
                return not original_updated_at == changed_updated_at

            wait_for(_wait_until_changes_applied, delay=10, timeout="5m")
        else:
            view.flash.assert_message(
                'Edit of Repository "{}" cancelled by the user.'.format(self.name))

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
            return True
        except ItemNotFound:
            return False

    def delete(self):
        """Delete the repository in the UI."""
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove this Repository", handle_alert=True)
        repo_list_page = self.create_view(RepositoryListView)
        assert repo_list_page.is_displayed
        repo_list_page.flash.assert_no_error()
        repo_list_page.flash.assert_message(
            'Delete of Repository "{}" was successfully initiated.'.format(self.name))
        wait_for(lambda: not self.exists, delay=10,
            fail_func=repo_list_page.browser.selenium.refresh)

    def refresh(self):
        """Perform a refresh to update the repository."""
        view = navigate_to(self, "Details")
        view.configuration.item_select("Refresh this Repository", handle_alert=True)
        view.flash.assert_no_error()
        view.flash.assert_message("Embedded Ansible refresh has been successfully initiated")

    @property
    def playbooks(self):
        return PlaybooksCollection(self)


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
            raise ItemNotFound


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
