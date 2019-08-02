# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.automate.explorer import AutomateExplorerView
from cfme.automate.explorer import check_tree_path
from cfme.automate.explorer.domain import Domain
from cfme.automate.explorer.domain import DomainDetailsView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from widgetastic_manageiq import Table


class NamespaceDetailsView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    namespaces = Table('#ns_details_grid')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Automate Namespace "{}"'.format(self.context['object'].name) and
            self.datastore.is_opened and (
                BZ(1704439).blocks or
                check_tree_path(
                    self.datastore.tree.currently_selected,
                    self.context['object'].tree_path)
            )
        )


class NamespaceForm(AutomateExplorerView):
    title = Text('#explorer_title_text')

    name = Input(name='ns_name')
    description = Input(name='ns_description')

    cancel_button = Button('Cancel')


class NamespaceAddView(NamespaceForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.datastore.is_opened and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path) and
            self.title.text == 'Adding a new Automate Namespace')


class NamespaceEditView(NamespaceForm):
    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.datastore.is_opened and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path) and
            self.title.text == 'Editing Automate Namespace "{}"'
                               .format(self.context['object'].name)
        )


class Namespace(BaseEntity):

    def __init__(self, collection, name, description=None):
        from cfme.automate.explorer.klass import ClassCollection
        self._collections = {
            'namespaces': NamespaceCollection,
            'classes': ClassCollection
        }
        super(Namespace, self).__init__(collection)
        self.name = name
        if description is not None:
            self.description = description

    __repr__ = object.__repr__

    def __hash__(self):
        return hash((self.name, id(self.parent)))

    @cached_property
    def description(self):
        return self.db_object.description

    @cached_property
    def db_id(self):
        table = self.appliance.db.client['miq_ae_namespaces']
        try:
            return self.appliance.db.client.session.query(table.id).filter(
                table.name == self.name,
                table.parent_id == self.parent_obj.db_id)[0]  # noqa
        except IndexError:
            raise ItemNotFound('Namespace named {} not found in the database'.format(self.name))

    @property
    def db_object(self):
        table = self.appliance.db.client['miq_ae_namespaces']
        return self.appliance.db.client.session.query(table).filter(table.id == self.db_id).first()

    @property
    def parent_obj(self):
        return self.parent.parent

    @property
    def domain(self):
        return self.parent_obj.domain

    @property
    def tree_path(self):
        return self.parent_obj.tree_path + [self.name]

    @cached_property
    def namespaces(self):
        return self.collections.namespaces

    @cached_property
    def classes(self):
        return self.collections.classes

    def delete(self, cancel=False):
        # Ensure this has correct data
        self.description
        # Do it!
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Remove this Namespace', handle_alert=not cancel)
        if cancel:
            assert details_page.is_displayed
            details_page.flash.assert_no_error()
        else:
            if isinstance(self.parent_obj, Domain):
                result_view = self.create_view(DomainDetailsView, self.parent_obj)
            else:
                result_view = self.create_view(NamespaceDetailsView, self.parent_obj)
            assert result_view.is_displayed
            result_view.flash.assert_no_error()
            result_view.flash.assert_message(
                'Automate Namespace "{}": Delete successful'.format(self.description or self.name))

            # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
            if BZ(1704439).blocks:
                self.browser.refresh()

    def update(self, updates):

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if BZ(1704439).blocks:
            self.browser.refresh()

        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()

        view = self.create_view(NamespaceDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            text = (updates.get('description', self.description) or updates.get('name', self.name))
            view.flash.assert_message('Automate Namespace "{}" was saved'.format(text))
        else:
            view.flash.assert_message(
                'Edit of Automate Namespace "{}" was cancelled by the user'.format(self.name))


@attr.s
class NamespaceCollection(BaseCollection):

    ENTITY = Namespace

    def __eq__(self, other):
        return self.parent == other.parent

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, name=None, description=None, cancel=False):
        add_page = navigate_to(self, 'Add')
        fill_dict = {
            k: v
            for k, v in list({'name': name, 'description': description}.items())
            if v is not None}
        add_page.fill(fill_dict)
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Namespace was cancelled by the user')
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message(
                'Automate Namespace "{}" was added'.format(description or name))

            # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
            if BZ(1704439).blocks:
                self.browser.refresh()

            return self.instantiate(name=name, description=description)

    def delete(self, *namespaces):
        all_page = navigate_to(self.parent, 'Details')
        namespaces = list(namespaces)
        parents = set()
        # Check if the parent is the same
        for namespace in namespaces:
            parents.add(namespace.parent.parent)
        if len(parents) > 1:
            raise ValueError('You passed namespaces that are not under one parent.')
        checked_namespaces = []
        if not all_page.namespaces.is_displayed:
            raise ValueError('No namespace found!')
        all_page.namespaces.uncheck_all()
        for row in all_page.namespaces.rows(_row__attr_startswith=('data-click-id', 'aen-')):
            name = row[2].text
            for namespace in namespaces:
                if namespace.name == name:
                    checked_namespaces.append(namespace)
                    row[0].check()
                    break

            if set(namespaces) == set(checked_namespaces):
                break

        if set(namespaces) != set(checked_namespaces):
            raise ValueError('Some of the namespaces were not found in the UI.')

        if isinstance(self.parent, Domain):
            all_page.configuration.item_select('Remove Namespaces', handle_alert=True)
        else:
            all_page.configuration.item_select('Remove selected Items', handle_alert=True)
        all_page.flash.assert_no_error()
        for namespace in checked_namespaces:
            all_page.flash.assert_message(
                'Automate Namespace "{}": Delete successful'.format(
                    namespace.description or namespace.name))

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if BZ(1704439).blocks:
            self.browser.refresh()


@navigator.register(NamespaceCollection)
class Add(CFMENavigateStep):
    VIEW = NamespaceAddView
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a New Namespace')


@navigator.register(Namespace)
class Details(CFMENavigateStep):
    VIEW = NamespaceDetailsView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self, *args, **kwargs):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(Namespace)
class Edit(CFMENavigateStep):
    VIEW = NamespaceEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit this Namespace')
