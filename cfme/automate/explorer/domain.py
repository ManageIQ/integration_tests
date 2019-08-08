# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import Fillable
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.xpath import quote
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
from widgetastic_patternfly import Input

from cfme.automate.explorer import AutomateExplorerView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils import clear_property_cache
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Table
from widgetastic_manageiq import UpDownSelect


def generate_updown(title):
    return './/*[(self::a or self::button) and @title={}]/*[self::img or self::i]'.format(
        quote(title))


class DomainRefreshView(AutomateExplorerView):
    title = Text("#explorer_title_text")
    branch_or_tag = BootstrapSelect(id="branch_or_tag_select")
    git_branches = BootstrapSelect(id="git_branches")

    save_button = Button("Save")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return (self.in_explorer
                and self.title.text == "Refreshing branch/tag for Git-based Domain")


class DomainPriorityView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    domains = UpDownSelect(
        '#seq_fields',
        generate_updown('Move selected fields up'),
        generate_updown('Move selected fields down'))

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Datastore' and
            self.domains.is_displayed)


class DomainListView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    domains = Table('#ns_list_grid')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Datastore' and
            self.datastore.is_opened and
            self.datastore.tree.currently_selected == ['Datastore'])


class DomainForm(AutomateExplorerView):
    title = Text('#explorer_title_text')

    name = Input(name='ns_name')
    description = Input(name='ns_description')
    enabled = Checkbox(name='ns_enabled')

    cancel_button = Button('Cancel')


class DomainAddView(DomainForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Adding a new Automate Domain')


class DomainEditView(DomainForm):
    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Editing Automate Domain "{}"'.format(self.context['object'].name))


class Domain(BaseEntity, Fillable):
    """A class representing one Domain in the UI."""

    def __init__(
            self, collection, name, description=None, enabled=None, locked=None,
            git_repository=None, git_checkout_type=None, git_checkout_value=None, db_id=None):
        from cfme.automate.explorer.namespace import NamespaceCollection
        self._collections = {'namespaces': NamespaceCollection}
        super(Domain, self).__init__(collection)
        self.name = name
        self.description = description
        if db_id is not None:
            self.db_id = db_id
        if git_repository is not None:
            self.git_repository = git_repository
        if git_checkout_type is not None:
            self.git_checkout_type = git_checkout_type
        if git_checkout_value is not None:
            self.git_checkout_value = git_checkout_value
        if enabled is not None:
            self.enabled = enabled
        if locked is not None:
            self.locked = locked

    __repr__ = object.__repr__

    # TODO this needs replacing with something better
    def __hash__(self):
        return hash((self.name, id(self.parent)))

    def as_fill_value(self):
        return self.name

    @cached_property
    def db_id(self):
        table = self.appliance.db.client['miq_ae_namespaces']
        try:
            return self.appliance.db.client.session.query(table.id).filter(
                table.name == self.name,
                table.parent_id == None)[0]  # noqa
        except IndexError:
            raise ItemNotFound('Domain named {} not found in the database'.format(self.name))

    @cached_property
    def git_repository(self):
        """Returns an associated git repository object. None if no git repo associated."""
        dbo = self.db_object
        if dbo.git_repository_id is None:
            return None
        return self.appliance.collections.automate_import_exports.git_repository_from_db(
            dbo.git_repository_id
        )

    @cached_property
    def git_checkout_type(self):
        return self.db_object.ref_type

    @cached_property
    def git_checkout_value(self):
        return self.db_object.ref

    @property
    def db_object(self):
        if self.db_id is None:
            return None
        table = self.appliance.db.client['miq_ae_namespaces']
        return self.appliance.db.client.session.query(table).filter(table.id == self.db_id).first()

    @cached_property
    def enabled(self):
        return self.db_object.enabled

    @cached_property
    def locked(self):
        return self.db_object.source in {'user_locked', 'system', 'remote'}

    @property
    def domain(self):
        return self

    @cached_property
    def namespaces(self):
        return self.collections.namespaces

    @property
    def tree_display_name(self):
        if self.git_repository:
            name = '{name} ({ref}) ({name})'.format(name=self.name, ref=self.git_checkout_value)
        else:
            name = self.name

        if self.locked and not self.enabled:
            return '{} (Locked & Disabled)'.format(name)
        elif self.locked and self.enabled:
            return '{} (Locked)'.format(name)
        elif not self.locked and not self.enabled:
            return '{} (Disabled)'.format(name)
        else:
            return name

    @property
    def table_display_name(self):
        if self.git_repository:
            name = '{name} ({ref})'.format(name=self.name, ref=self.git_checkout_value)
        else:
            name = self.name

        if self.locked and not self.enabled:
            return '{} (Locked & Disabled)'.format(name)
        elif self.locked and self.enabled:
            return '{} (Locked)'.format(name)
        elif not self.locked and not self.enabled:
            return '{} (Disabled)'.format(name)
        else:
            return name

    @property
    def tree_path(self):
        return self.parent.tree_path + [self.tree_display_name]

    def delete(self, cancel=False):
        # Ensure this has correct data
        self.description
        # Do it!
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Remove this Domain', handle_alert=not cancel)
        if cancel:
            assert details_page.is_displayed
            details_page.flash.assert_no_error()
        else:
            domains_view = self.create_view(DomainListView)
            assert domains_view.is_displayed
            domains_view.flash.assert_no_error()
            domains_view.flash.assert_message(
                'Automate Domain "{}": Delete successful'.format(self.description or self.name))

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if False:
            self.browser.refresh()

    def lock(self):
        # Ensure this has correct data
        self.description
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Lock this Domain')
        details_page.flash.assert_no_error()
        details_page.flash.assert_message('The selected Automate Domain were marked as Locked')

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if False:
            self.browser.refresh()

        clear_property_cache(self, 'locked')
        assert self.locked

    def unlock(self):
        # Ensure this has correct data
        self.description
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Unlock this Domain')
        details_page.flash.assert_no_error()
        details_page.flash.assert_message('The selected Automate Domain were marked as Unlocked')

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if False:
            self.browser.refresh()

        clear_property_cache(self, 'locked')
        assert not self.locked

    def update(self, updates):

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if False:
            self.browser.refresh()

        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(DomainDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            text = (updates.get('description', self.description)
                    or updates.get('name', self.name))
            view.flash.assert_message('Automate Domain "{}" was saved'.format(text))
        else:
            view.flash.assert_message(
                'Edit of Automate Domain "{}" was cancelled by the user'.format(self.name))

    def refresh(self, branch_or_tag=None, git_branch=None, cancel=False):
        view = navigate_to(self, 'Refresh')

        # It refreshes the domain for default values of 'branch_or_tag' and 'git_branch'; if these
        # values are not provided while calling 'refresh' then imported domain should be refreshed
        # with default values of 'branch_or_tag' and 'git_branches'.

        changed = view.fill(
            {
                'branch_or_tag': branch_or_tag or view.branch_or_tag.selected_option,
                'git_branches': git_branch or view.git_branches.selected_option
            }
        )

        if changed and not cancel:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view.flash.assert_no_error()


@attr.s
class DomainCollection(BaseCollection):
    """Collection object for the :py:class:`Domain`."""
    tree_path = ['Datastore']
    ENTITY = Domain

    def create(self, name=None, description=None, enabled=None, cancel=False):
        add_page = navigate_to(self, 'Add')
        fill_dict = {
            k: v
            for k, v in {
                'name': name,
                'description': description,
                'enabled': enabled
            }.items()
            if v is not None
        }
        add_page.fill(fill_dict)
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Domain was cancelled by the user')
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message(
                'Automate Domain "{}" was added'.format(description or name))

            if enabled is None:
                # Assume
                enabled = False

            # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
            if False:
                self.browser.refresh()

            return self.instantiate(
                name=name, description=description, enabled=enabled, locked=False)

    def all(self):
        table = self.appliance.db.client['miq_ae_namespaces']
        query = self.appliance.db.client.session.query(
            table.name, table.description, table.enabled, table.source, table.ref, table.ref_type,
            table.git_repository_id)
        query = query.filter(table.name != '$', table.parent_id == None)  # noqa
        result = []
        for name, description, enabled, source, ref, ref_type, git_repository_id in query:
            if source != 'remote':
                result.append(
                    self.instantiate(
                        name=name,
                        description=description or '',
                        enabled=enabled,
                        locked=source in {'user_locked', 'system'}))
            else:
                repo_table = self.appliance.db.client['git_repositories']
                repo = self.appliance.db.client.session\
                    .query(repo_table)\
                    .filter(repo_table.id == git_repository_id)\
                    .first()
                agr = self.appliance.collections.automate_import_exports.instantiate(
                    import_type="git", url=repo.url, verify_ssl=repo.verify_ssl
                )
                result.append(
                    self.instantiate(
                        name=name,
                        description=description,
                        enabled=enabled,
                        locked=True,
                        git_repository=agr,
                        git_checkout_type=ref_type,
                        git_checkout_value=ref))
        return result

    def delete(self, *domains):
        domains = list(domains)
        checked_domains = []
        all_page = navigate_to(self, 'All')
        all_page.domains.uncheck_all()
        if not all_page.domains.is_displayed:
            raise ValueError('No domain found!')
        for row in all_page.domains:
            for domain in domains:
                if domain.table_display_name == row.name.text:
                    checked_domains.append(domain)
                    row[0].check()
                    break

            if set(domains) == set(checked_domains):
                break

        if set(domains) != set(checked_domains):
            raise ValueError('Some of the domains were not found in the UI.')

        all_page.configuration.item_select('Remove Domains', handle_alert=True)
        all_page.flash.assert_no_error()
        for domain in checked_domains:
            all_page.flash.assert_message(
                'Automate Domain "{}": Delete successful'.format(domain.description or domain.name))

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if False:
            self.browser.refresh()

    def set_order(self, items):
        if not isinstance(items, (list, tuple)):
            items = [items]

        processed_items = [Fillable.coerce(item) for item in items]
        priority_page = navigate_to(self, 'Priority')
        changed = priority_page.domains.fill(processed_items)
        if changed:
            # Changed
            priority_page.save_button.click()
        else:
            # Not changed
            priority_page.cancel_button.click()
        domains_view = self.create_view(DomainListView)
        assert domains_view.is_displayed
        domains_view.flash.assert_no_error()
        if changed:
            domains_view.flash.assert_message('Priority Order was saved')
        else:
            domains_view.flash.assert_message('Edit of Priority Order was cancelled by the user')
        return changed


@navigator.register(DomainCollection)
class All(CFMENavigateStep):
    VIEW = DomainListView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self, *args, **kwargs):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(DomainCollection)
class Add(CFMENavigateStep):
    VIEW = DomainAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a New Domain')


@navigator.register(DomainCollection)
class Priority(CFMENavigateStep):
    VIEW = DomainPriorityView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit Priority Order of Domains')


@navigator.register(Domain)
class Refresh(CFMENavigateStep):
    VIEW = DomainRefreshView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Refresh with a new branch or tag')


class DomainDetailsView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    namespaces = Table('#ns_details_grid')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Automate Domain "{}"'.format(
                self.context['object'].table_display_name))


@navigator.register(Domain)
class Details(CFMENavigateStep):
    VIEW = DomainDetailsView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)
        except CandidateNotFound:
            # Try it with regexp (drop the locked to None)
            # That will force reload from database
            self.obj.locked = None
            self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(Domain)
class Edit(CFMENavigateStep):
    VIEW = DomainEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit this Domain')
