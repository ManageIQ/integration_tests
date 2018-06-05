# -*- coding: utf-8 -*-
from cfme.base.ui import AutomateImportExportBaseView, AutomateImportExportView
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to

from widgetastic_patternfly import BootstrapSelect, Button


class GitImportSelectorView(AutomateImportExportBaseView):
    type = BootstrapSelect('branch_or_tag')
    branch = BootstrapSelect(locator='.//div[contains(@class, "bootstrap-select git-branches")]')
    tag = BootstrapSelect(locator='.//div[contains(@class, "bootstrap-select git-tags")]')

    submit = Button('Submit')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.in_import_export and self.type.is_displayed


class AutomateGitRepository(Navigatable):
    """Represents an Automate git repository. This entity is not represented in UI as it is, but
    only in database. But by representing it it makes the code changes for domain much simpler.

    """
    def __init__(self, url=None, username=None, password=None, verify_ssl=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.url = url
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.domain = None

    @classmethod
    def from_db(cls, db_id, appliance=None):
        git_repositories = appliance.db.client['git_repositories']
        try:
            url, verify_ssl = appliance.db.client.session\
                .query(git_repositories.url, git_repositories.verify_ssl)\
                .filter(git_repositories.id == db_id)\
                .first()
            return cls(url=url, verify_ssl=verify_ssl > 0, appliance=appliance)
        except ValueError:
            raise ValueError('No such repository in the database')

    @property
    def fill_values_repo_add(self):
        return {
            k: v
            for k, v
            in {
                'url': self.url,
                'username': self.username,
                'password': self.password,
                'verify_ssl': self.verify_ssl}.items() if v is not None}

    def fill_values_branch_select(self, branch, tag):
        """Processes the args into a dictionary to be filled in the selection dialog."""
        if branch and tag:
            raise ValueError('You cannot pass branch and tag together')
        elif tag is not None:
            return {'type': 'Tag', 'tag': tag}
        else:
            return {'type': 'Branch', 'branch': branch}

    def import_domain_from(self, branch=None, tag=None):
        """Import the domain from git using the Import/Export UI.

        Args:
            branch: If you import from a branch, specify the origin/branchname
            tag: If you import from a tag, specify its name.

        Returns:
            Instance of :py:class:`cfme.automate.explorer.domain.Domain`

        **Important!** ``branch`` and ``tag`` are mutually exclusive.
        """
        imex_page = navigate_to(self.appliance.server, 'AutomateImportExport')
        assert imex_page.import_git.fill(self.fill_values_repo_add)
        imex_page.import_git.submit.click()
        imex_page.browser.plugin.ensure_page_safe(timeout='5m')
        git_select = self.create_view(GitImportSelectorView)
        assert git_select.is_displayed
        git_select.flash.assert_no_error()
        git_select.fill(self.fill_values_branch_select(branch, tag))
        git_select.submit.click()
        git_select.browser.plugin.ensure_page_safe(timeout='5m')
        imex_page = self.create_view(AutomateImportExportView)
        assert imex_page.is_displayed
        imex_page.flash.assert_no_error()
        # Now find the domain in database
        namespaces = self.appliance.db.client['miq_ae_namespaces']
        git_repositories = self.appliance.db.client['git_repositories']
        none = None
        query = self.appliance.db.client.session\
            .query(
                namespaces.id, namespaces.name, namespaces.description, git_repositories.url,
                namespaces.ref_type, namespaces.ref)\
            .filter(namespaces.parent_id == none, namespaces.source == 'remote')\
            .join(git_repositories, namespaces.git_repository_id == git_repositories.id)
        for id, name, description, url, git_type, git_type_value in query:
            if url != self.url:
                continue
            if not (
                    git_type == 'branch' and branch == git_type_value or
                    git_type == 'tag' and tag == git_type_value):
                continue
            # We have the domain
            dc = self.appliance.collections.domains
            return dc.instantiate(
                db_id=id, name=name, description=description, git_checkout_type=git_type,
                git_checkout_value=git_type_value)
        else:
            raise ValueError('The domain imported was not found in the database!')
