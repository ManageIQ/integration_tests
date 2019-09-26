# -*- coding: utf-8 -*-
"""Page model for Automation/Ansible/Repositories"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Checkbox
from widgetastic.widget import Fillable
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.ansible.playbooks import PlaybooksCollection
from cfme.base.login import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import Table


class RepositoryBaseView(BaseLoggedInPage):
    title = Text(locator='.//div[@id="main-content"]//h1')

    @property
    def in_ansible_repositories(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Ansible", "Repositories"]
        )


class RepositoryAllView(RepositoryBaseView):
    @View.nested
    class toolbar(View):   # noqa
        configuration = Dropdown("Configuration")
        policy = Dropdown(text='Policy')

    entities = Table(".//div[@id='gtl_div']//table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return self.in_ansible_repositories and self.title.text == "Repositories"


class RepositoryDetailsView(RepositoryBaseView):

    @View.nested
    class toolbar(View):  # noqa
        refresh = Button(title="Refresh this page")
        configuration = Dropdown("Configuration")
        download = Button(title="Print or export summary")
        policy = Dropdown(text='Policy')

    @View.nested
    class entities(View):  # noqa
        summary = ParametrizedView.nested(ParametrizedSummaryTable)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == self.context["object"].expected_details_title
        )


class RepositoryPlaybooksView(RepositoryDetailsView):

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == "{} (All Playbooks)".format(self.context['object'].name)
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


@attr.s
class Repository(BaseEntity, Fillable, Taggable):
    """A class representing one Embedded Ansible repository in the UI."""

    name = attr.ib()
    url = attr.ib()
    description = attr.ib(default="")
    scm_credentials = attr.ib(default=None)
    scm_branch = attr.ib(default=False)
    clean = attr.ib(default=False)
    delete_on_update = attr.ib(default=False)
    update_on_launch = attr.ib(default=None)

    _collections = {'playbooks': PlaybooksCollection}

    @property
    def db_object(self):
        table = self.appliance.db.client["configuration_script_sources"]
        return self.appliance.db.client.sessionmaker(autocommit=True).query(table).filter(
            table.name == self.name).first()

    @property
    def playbooks(self):
        return self.collections.playbooks

    @property
    def as_fill_value(self):
        """For use when selecting this repo in the UI forms"""
        return self.name

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
        view = self.create_view(RepositoryAllView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message('Edit of Repository "{}" was successfully initiated.'
                                      .format(updates.get("name", self.name)))

            def _wait_until_changes_applied():
                changed_updated_at = self.db_object.updated_at
                return not original_updated_at == changed_updated_at

            wait_for(_wait_until_changes_applied, delay=10, timeout="5m")
        else:
            view.flash.assert_message(
                'Edit of Repository "{}" cancelled by the user.'.format(self.name))

    def delete(self):
        """Delete the repository in the UI."""
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Remove this Repository from Inventory",
                                               handle_alert=True)
        repo_list_page = self.create_view(RepositoryAllView)
        assert repo_list_page.is_displayed
        repo_list_page.flash.assert_no_error()
        repo_list_page.flash.assert_message(
            'Delete of Repository "{}" was successfully initiated.'.format(self.name))
        wait_for(
            lambda: not self.exists,
            delay=10,
            timeout=300,
            fail_func=repo_list_page.browser.selenium.refresh)

    def refresh(self):
        """Perform a refresh to update the repository."""
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Refresh this Repository", handle_alert=True)
        view.flash.assert_no_error()
        view.flash.assert_message("Embedded Ansible refresh has been successfully initiated")


@attr.s
class RepositoryCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.ansible.repositories.Repository`."""

    ENTITY = Repository

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
        repo_list_page = self.create_view(RepositoryAllView)
        assert repo_list_page.is_displayed
        repo_list_page.flash.assert_no_error()
        repo_list_page.flash.assert_message('Add of Repository "{}" was successfully initiated.'
                                            .format(name))

        repository = self.instantiate(
            name,
            url,
            description=description,
            scm_credentials=scm_credentials,
            scm_branch=scm_branch,
            clean=clean,
            delete_on_update=delete_on_update,
            update_on_launch=update_on_launch)

        wait_for(
            lambda: repository.exists,
            fail_func=repo_list_page.browser.refresh,
            delay=5,
            timeout=1080,
            message=f'Waiting for "{name}" repository',
        )

        return repository

    def all(self):
        """Return all repositories of the appliance.

        Returns: a :py:class:`list` of :py:class:`cfme.ansible.repositories.Repository` instances
        """
        table = self.appliance.db.client["configuration_script_sources"]
        result = []
        for row in self.appliance.db.client.session.query(table):
            result.append(
                self.instantiate(
                    row.name,
                    row.scm_url,
                    description=row.description,
                    scm_branch=row.scm_branch,
                    clean=row.scm_clean,
                    delete_on_update=row.scm_delete_on_update,
                    update_on_launch=row.scm_update_on_launch)
            )
        return result

    def delete(self, *repositories):
        """Delete one or more ansible repositories in the UI.

        Args:
            repositories: a list of :py:class:`cfme.ansible.repositories.Repository`
                          instances to delete

        Raises:
            ValueError: if some of the repositories were not found in the UI
        """
        repositories = list(repositories)
        checked_repositories = []
        view = navigate_to(self.appliance.server, "AnsibleRepositories")
        view.paginator.uncheck_all()
        if not view.entities.is_displayed:
            raise ValueError("No repository found!")
        for row in view.entities:
            for repository in repositories:
                if repository.name == row.name.text:
                    checked_repositories.append(repository)
                    row[0].check()
                    break
            if set(repositories) == set(checked_repositories):
                break
        if set(repositories) != set(checked_repositories):
            raise ValueError("Some of the repositories were not found in the UI.")
        view.toolbar.configuration.item_select("Remove selected Repositories", handle_alert=True)
        view.flash.assert_no_error()
        for repository in checked_repositories:
            view.flash.assert_message(
                'Delete of Repository "{}" was successfully initiated.'.format(repository.name))


@navigator.register(RepositoryCollection, 'All')
class AnsibleRepositories(CFMENavigateStep):
    VIEW = RepositoryAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.view.navigation.select("Automation", "Ansible", "Repositories")


@navigator.register(Repository, 'Details')
class Details(CFMENavigateStep):
    VIEW = RepositoryDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                table=self.prerequisite_view.entities,
                name=self.obj.name)
            row.click()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate ansible repository table row with name {}'
                               .format(self.obj.name))


@navigator.register(RepositoryCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = RepositoryAddView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        # workaround for disabled Dropdown
        dropdown = self.prerequisite_view.toolbar.configuration
        wait_for(
            lambda: dropdown.is_enabled,
            timeout=120,
            fail_func=self.prerequisite_view.browser.refresh,
            message="Waiting for configuration [Add New Repository] enable",
        )
        dropdown.item_select("Add New Repository")


@navigator.register(Repository, "Edit")
class Edit(CFMENavigateStep):
    VIEW = RepositoryEditView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Repository")


@navigator.register(Repository, "Playbooks")
class RepositoryPlaybooks(CFMENavigateStep):
    VIEW = RepositoryPlaybooksView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.summary("Relationships").click_at("Playbooks")


@navigator.register(Repository, 'EditTags')
class EditTagsFromListCollection(CFMENavigateStep):
    VIEW = TagPageView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                table=self.prerequisite_view.entities,
                name=self.obj.name)
            row[0].check()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate ansible repository table row with name {}'
                               .format(self.obj.name))
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
