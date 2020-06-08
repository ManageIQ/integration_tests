import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Checkbox
from widgetastic.widget import FileInput
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.common import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import ImportExportFlashMessages


class AutomateImportExportBaseView(BaseLoggedInPage):
    flash = View.nested(ImportExportFlashMessages)

    title = Text('.//div[@id="main-content"]//h1')

    @property
    def in_import_export(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ["Automation", "Automate", "Import / Export"]
            and self.title.text == "Import / Export"
        )

    @property
    def is_displayed(self):
        return self.in_import_export


class AutomateImportExportView(AutomateImportExportBaseView):

    @View.nested
    class import_file(View):  # noqa
        upload_file = FileInput(id="upload_file")
        upload = Button(id="upload-datastore-import")

    @View.nested
    class import_git(View):  # noqa
        ROOT = './/form[@id="retrieve-git-datastore-form"]'

        url = Input(name="git_url")
        username = Input(name="git_username")
        password = Input(name="git_password")
        verify_ssl = Checkbox(name="git_verify_ssl")
        submit = Button(id="git-url-import")

    export_all = Button(title="Export all classes and instances")
    reset_all = Button(title="Reset all components in the following domains: RedHat, ManageIQ")
    reset_title = Text(
        ".//div[contains(@class, 'import-or-export')]/h3[contains(text(), 'Reset all')]"
    )

    @property
    def is_displayed(self):
        title = "Reset all components in the following domains: RedHat, ManageIQ"

        return (
            self.in_import_export
            and self.export_all.is_displayed
            and self.reset_title.text == title
        )


class FileImportSelectorView(AutomateImportExportBaseView):

    import_into = BootstrapSelect(id="selected_domain_to_import_to")
    import_from = BootstrapSelect(
        locator=".//div[contains(@class, 'bootstrap-select importing-domains')]"
    )
    toggle_all = Checkbox(id="toggle-all")

    commit = Button("Commit")
    back = Button("Back")

    @property
    def is_displayed(self):
        return (
            self.in_import_export
            and self.import_from.is_displayed
            and self.import_into.is_displayed
        )


class GitImportSelectorView(AutomateImportExportBaseView):
    branch_tag = BootstrapSelect("branch_or_tag")
    branch = BootstrapSelect(locator='.//div[contains(@class, "bootstrap-select git-branches")]')
    tag = BootstrapSelect(locator='.//div[contains(@class, "bootstrap-select git-tags")]')

    submit = Button("Submit")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return self.in_import_export and self.branch_tag.is_displayed


@attr.s
class AutomateGitRepository(BaseEntity):
    url = attr.ib()
    username = attr.ib(default=None)
    password = attr.ib(default=None)
    verify_ssl = attr.ib(default=None)
    domain = attr.ib(default=None)

    def import_domain_from(self, branch=None, tag=None):
        """Import the domain from git using the Import/Export UI.

        Args:
            branch: If you import from a branch, specify the origin/branchname
            tag: If you import from a tag, specify its name.

        Returns:
            Instance of :py:class:`cfme.automate.explorer.domain.Domain`

        **Important!** ``branch`` and ``tag`` are mutually exclusive.
        """
        if branch and tag:
            raise ValueError("You cannot pass branch and tag together")
        elif branch:
            branch_tag = "Branch"
        else:
            branch_tag = "Tag"

        view = navigate_to(self.parent, "All")
        view.import_git.fill(
            {
                "url": self.url,
                "username": self.username,
                "password": self.password,
                "verify_ssl": self.verify_ssl,
            }
        )
        view.import_git.submit.click()
        view.flash.assert_no_error()

        git_select_view = self.create_view(GitImportSelectorView, wait="10s")
        git_select_view.flash.assert_no_error()
        git_select_view.fill({"branch_tag": branch_tag, "branch": branch, "tag": tag})
        git_select_view.submit.click()
        view.flash.assert_no_error()

        # Now find the domain in database
        # TODO: find way to implement it with rest client
        namespaces = self.appliance.db.client["miq_ae_namespaces"]
        git_repositories = self.appliance.db.client["git_repositories"]
        none = None
        query = (
            self.appliance.db.client.session.query(
                namespaces.id,
                namespaces.name,
                namespaces.description,
                git_repositories.url,
                namespaces.ref_type,
                namespaces.ref,
            )
            .filter(namespaces.parent_id == none, namespaces.source == "remote")
            .join(git_repositories, namespaces.git_repository_id == git_repositories.id)
        )

        for db_id, name, description, repo_url, git_type, git_type_value in query:
            if self.url != repo_url:
                continue
            if not (
                git_type == "branch"
                and branch == git_type_value
                or git_type == "tag"
                and tag == git_type_value
            ):
                continue

            # We have the domain
            return self.appliance.collections.domains.instantiate(
                db_id=db_id,
                name=name,
                description=description,
                git_checkout_type=git_type,
                git_checkout_value=git_type_value,
            )
        else:
            raise ValueError("The domain imported was not found in the database!")


@attr.s
class AutomateFileImport(BaseEntity):
    file_path = attr.ib()

    def import_domain_from(self, domain_from, domain_into=None, toggle_all=True):
        """Import the domain from file using the Import/Export UI.

        Args:
            domain_from: Select domain you wish to import from
            domain_into: Select existing domain to import into:
            toggle_all: Select all namespaces

        Returns:
            Instance of :py:class:`cfme.automate.explorer.domain.Domain`
        """
        view = navigate_to(self.parent, "All")
        view.import_file.upload_file.fill(self.file_path)
        view.import_file.upload.click()

        file_view = self.create_view(FileImportSelectorView, wait="10s")
        file_view.fill(
            {"import_into": domain_into, "import_from": domain_from, "toggle_all": toggle_all}
        )
        file_view.commit.click()
        return self.appliance.collections.domains.instantiate(name=domain_from)


@attr.s
class AutomateImportExportsCollection(BaseCollection):
    def instantiate(
        self,
        import_type="git",
        url=None,
        username=None,
        password=None,
        verify_ssl=True,
        file_path=None,
        **kwargs
    ):
        if import_type == "file":
            import_cls = AutomateFileImport
            args = [file_path]
        elif import_type == "git":
            import_cls = AutomateGitRepository
            args = [url, username, password, verify_ssl]

        return import_cls.from_collection(self, *args, **kwargs)

    def git_repository_from_db(self, db_id):
        """Instantiate AutomateGitRepository with db id"""

        git_repositories = self.appliance.db.client["git_repositories"]
        try:
            url, verify_ssl = (
                self.appliance.db.client.session.query(
                    git_repositories.url, git_repositories.verify_ssl
                )
                .filter(git_repositories.id == db_id)
                .first()
            )
            return self.instantiate(import_type="git", url=url, verify_ssl=bool(verify_ssl))
        except ValueError:
            raise ValueError("No such repository in the database")

    def export_datastores(self):
        """Export all classes and instances to a file"""
        view = navigate_to(self, "All")
        view.export_all.click()

    def reset_datastores(self):
        """Reset all components in the domains RedHat, ManageIQ"""
        view = navigate_to(self, "All")
        view.reset_all.click()


@navigator.register(AutomateImportExportsCollection, "All")
class AutomateImportExport(CFMENavigateStep):
    VIEW = AutomateImportExportView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Automation", "Automate", "Import / Export")
