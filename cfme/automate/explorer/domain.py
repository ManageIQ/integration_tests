# -*- coding: utf-8 -*-
import re

from cached_property import cached_property
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Checkbox
from widgetastic.utils import Fillable
from widgetastic_manageiq import Table, UpDownSelect
from widgetastic_patternfly import CandidateNotFound, Input, Button

from cfme.exceptions import ItemNotFound
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

from . import AutomateExplorerView


class DomainPriorityView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    domains = UpDownSelect(
        '#seq_fields',
        './/a[@title="Move selected fields up"]/img',
        './/a[@title="Move selected fields down"]/img')

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
            self.title.text == 'Editing Automate Domain "{}"'.format(self.obj.name))


class DomainCollection(Navigatable):
    """Collection object for the :py:class:`Domain`."""
    tree_path = ['Datastore']

    def instantiate(self, name, description=None, enabled=None):
        return Domain(
            name=name, description=description, enabled=enabled, locked=None,
            appliance=self.appliance)

    def create(self, name=None, description=None, enabled=None, cancel=False):
        add_page = navigate_to(self, 'Add')
        fill_dict = {
            k: v
            for k, v in {'name': name, 'description': description, 'enabled': enabled}.items()
            if v is not None}
        add_page.fill(fill_dict)
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Domain was cancelled by the user')
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Automate Domain "{}" was added'.format(name))
            if enabled is None:
                # Assume
                enabled = False
            return Domain(
                name=name, description=description, enabled=enabled, locked=False,
                appliance=self.appliance)

    def all(self):
        table = self.appliance.db['miq_ae_namespaces']
        query = self.appliance.db.session.query(
            table.name, table.description, table.enabled, table.source)
        query = query.filter(table.name != '$', table.parent_id == None)  # noqa
        result = []
        for name, description, enabled, source in query:
            result.append(
                Domain(
                    name=name,
                    description=description or '',
                    enabled=enabled,
                    locked=source in {'user_locked', 'system'},
                    appliance=self.appliance))
        return result

    def delete(self, *domains):
        domains = list(domains)
        checked_domains = []
        all_page = navigate_to(self, 'All')
        all_page.domains.uncheck_all()
        if not all_page.domains.is_displayed:
            raise ValueError('No domain found!')
        for row in all_page.domains:
            name = re.sub(r' \((?:Locked|Disabled|Locked & Disabled)\)$', '', row.name.text)
            for domain in domains:
                if domain.name == name:
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

    def step(self):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(DomainCollection)
class Add(CFMENavigateStep):
    VIEW = DomainAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a New Domain')


@navigator.register(DomainCollection)
class Priority(CFMENavigateStep):
    VIEW = DomainPriorityView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit Priority Order of Domains')


class DomainDetailsView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    namespaces = Table('#ns_details_grid')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            re.match(
                r'^Automate Domain "{}(?: \((?:Disabled|Locked|Locked & Disabled)\))?"$'.format(
                    re.escape(self.context['object'].name)),
                self.title.text) is not None)


class Domain(Navigatable, Fillable):
    """A class representing one Domain in the UI."""
    def __init__(
            self, name, description, enabled=None, locked=None, collection=None, appliance=None):
        if collection is None:
            collection = DomainCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=collection.appliance)
        self.name = name
        self.description = description
        if enabled is not None:
            self.enabled = enabled
        if locked is not None:
            self.locked = locked

    def as_fill_value(self):
        return self.name

    @cached_property
    def db_id(self):
        table = self.appliance.db['miq_ae_namespaces']
        try:
            return self.appliance.db.session.query(table.id).filter(
                table.name == self.name,
                table.parent_id == None)[0]  # noqa
        except IndexError:
            raise ItemNotFound('Domain named {} not found in the database'.format(self.name))

    @property
    def db_object(self):
        if self.db_id is None:
            return None
        table = self.appliance.db['miq_ae_namespaces']
        return self.appliance.db.session.query(table).filter(table.id == self.db_id).first()

    @cached_property
    def enabled(self):
        return self.db_object.enabled

    @cached_property
    def locked(self):
        if self.browser.product_version < '5.7':
            return self.db_object.system
        else:
            return self.db_object.source in {'user_locked', 'system'}

    @property
    def parent(self):
        return self.collection

    @property
    def domain(self):
        return self

    @cached_property
    def namespaces(self):
        from .namespace import NamespaceCollection
        return NamespaceCollection(self)

    @property
    def tree_path(self):
        if self.locked and not self.enabled:
            result = '{} (Locked & Disabled)'.format(self.name)
        elif self.locked and self.enabled:
            result = '{} (Locked)'.format(self.name)
        elif not self.locked and not self.enabled:
            result = '{} (Disabled)'.format(self.name)
        else:
            result = self.name

        return self.collection.tree_path + [result]

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

    def update(self, updates):
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
            view.flash.assert_message(
                'Automate Domain "{}" was saved'.format(updates.get('name', self.name)))
        else:
            view.flash.assert_message(
                'Edit of Automate Domain "{}" was cancelled by the user'.format(self.name))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except (CandidateNotFound, ItemNotFound):
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@navigator.register(Domain)
class Details(CFMENavigateStep):
    VIEW = DomainDetailsView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self):
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

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Domain')
