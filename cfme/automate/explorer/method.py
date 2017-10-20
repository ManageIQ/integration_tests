# -*- coding: utf-8 -*-
import attr

from cached_property import cached_property
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text
from widgetastic_manageiq import SummaryFormItem, ScriptBox, Input
from widgetastic_patternfly import BootstrapSelect, Button, CandidateNotFound

from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.timeutil import parsetime

from . import AutomateExplorerView, check_tree_path
from .common import Copiable, CopyViewBase
from .klass import ClassDetailsView


class MethodCopyView(AutomateExplorerView, CopyViewBase):
    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Copy Automate Method' and
            self.datastore.is_opened and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path))


class MethodDetailsView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    fqdn = SummaryFormItem(
        'Main Info', 'Fully Qualified Name',
        text_filter=lambda text: [item.strip() for item in text.strip().lstrip('/').split('/')])
    name = SummaryFormItem('Main Info', 'Name')
    display_name = SummaryFormItem('Main Info', 'Display Name')
    location = SummaryFormItem('Main Info', 'Location')
    created_on = SummaryFormItem('Main Info', 'Created On', text_filter=parsetime.from_iso_with_utc)

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text.startswith('Automate Method [{}'.format(
                self.context['object'].display_name or self.context['object'].name)) and
            self.fqdn.is_displayed and
            # We need to chop off the leading Domain name.
            self.fqdn.text == self.context['object'].tree_path_name_only[1:])


class MethodAddView(AutomateExplorerView):
    title = Text('#explorer_title_text')

    location = BootstrapSelect('cls_method_location', can_hide_on_select=True)
    name = Input(name='cls_method_name')
    display_name = Input(name='cls_method_display_name')

    script = ScriptBox()
    data = Input(name='cls_method_data')

    validate_button = Button('Validate')
    add_button = Button('Add')
    cancel_button = Button('Cancel')

    # TODO: Input parameters

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.datastore.is_opened and
            self.title.text == 'Adding a new Automate Method' and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path))


class MethodEditView(AutomateExplorerView):
    title = Text('#explorer_title_text')

    name = Input(name='method_name')
    display_name = Input(name='method_display_name')
    location = BootstrapSelect('method_location')

    script = ScriptBox()
    data = Input(name='method_data')

    validate_button = Button('Validate')
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    # TODO: Input parameters

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.datastore.is_opened and
            self.title.text == 'Editing Automate Method "{}"'.format(
                self.context['object'].name) and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path))


class Method(BaseEntity, Copiable):
    def __init__(self, collection, name, display_name=None, location=None, script=None, data=None):
        super(Method, self).__init__(collection)

        self.name = name
        if display_name is not None:
            self.display_name = display_name
        self.location = location
        self.script = script
        self.data = data

    __repr__ = object.__repr__

    @cached_property
    def display_name(self):
        return self.db_object.display_name

    @cached_property
    def db_id(self):
        table = self.appliance.db.client['miq_ae_methods']
        try:
            return self.appliance.db.client.session.query(table.id).filter(
                table.name == self.name,
                table.class_id == self.klass.db_id)[0]  # noqa
        except IndexError:
            raise ItemNotFound('Method named {} not found in the database'.format(self.name))

    @property
    def db_object(self):
        table = self.appliance.db.client['miq_ae_methods']
        return self.appliance.db.client.session.query(table).filter(table.id == self.db_id).first()

    @property
    def klass(self):
        return self.parent_obj

    @property
    def namespace(self):
        return self.klass.namespace

    @property
    def parent_obj(self):
        return self.parent.parent

    @property
    def domain(self):
        return self.parent_obj.domain

    @property
    def tree_path(self):
        if self.display_name:
            return self.parent_obj.tree_path + ['{} ({})'.format(self.display_name, self.name)]
        else:
            return self.parent_obj.tree_path + [self.name]

    @property
    def tree_path_name_only(self):
        return self.parent_obj.tree_path_name_only + [self.name]

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(MethodDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Automate Method "{}" was saved'.format(updates.get('name', self.name)))
        else:
            view.flash.assert_message(
                'Edit of Automate Method "{}" was cancelled by the user'.format(self.name))

    def delete(self, cancel=False):
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Remove this Method', handle_alert=not cancel)
        if cancel:
            assert details_page.is_displayed
            details_page.flash.assert_no_error()
        else:
            result_view = self.create_view(ClassDetailsView, self.parent_obj)
            assert result_view.is_displayed
            result_view.flash.assert_no_error()
            result_view.flash.assert_message(
                'Automate Method "{}": Delete successful'.format(self.name))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except CandidateNotFound:
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@attr.s
class MethodCollection(BaseCollection):

    ENTITY = Method

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(
            self, name=None, display_name=None, location='inline', script=None, data=None,
            cancel=False, validate=True):
        add_page = navigate_to(self, 'Add')
        fill_dict = {
            k: v
            for k, v in {
                'name': name,
                'display_name': display_name,
                'location': location,
                'script': script,
                'data': data,
            }.items()
            if v is not None}
        add_page.fill(fill_dict)
        if validate:
            add_page.validate_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Data validated successfully')
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Method was cancelled by the user')
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Automate Method "{}" was added'.format(name))
            return self.instantiate(
                name=name,
                display_name=display_name,
                location=location,
                script=script,
                data=data)

    def delete(self, *methods):
        all_page = navigate_to(self.parent, 'Details')
        all_page.methods.select()
        methods = list(methods)
        parents = set()
        for method in methods:
            parents.add(method.parent)
        if len(parents) > 1:
            raise ValueError('You passed methods that are not under one class.')

        checked_methods = []
        if not all_page.methods.table.is_displayed:
            raise ValueError('No method found!')
        all_page.methods.table.uncheck_all()
        for row in all_page.instances.table:
            name = row[2].text
            for method in methods:
                if (
                        (method.display_name and method.display_name == name) or
                        method.name == name):
                    checked_methods.append(method)
                    row[0].check()
                    break

            if set(methods) == set(checked_methods):
                break

        if set(methods) != set(checked_methods):
            raise ValueError('Some of the instances were not found in the UI.')

        all_page.configuration.item_select('Remove Methods', handle_alert=True)
        all_page.flash.assert_no_error()
        for method in checked_methods:
            all_page.flash.assert_message(
                'Automate Method "{}": Delete successful'.format(method.name))


@navigator.register(MethodCollection)
class Add(CFMENavigateStep):
    VIEW = MethodAddView
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        self.prerequisite_view.methods.select()
        self.prerequisite_view.configuration.item_select('Add a New Method')


@navigator.register(Method)
class Details(CFMENavigateStep):
    VIEW = MethodDetailsView
    prerequisite = NavigateToAttribute('domain', 'Details')

    def step(self):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(Method)
class Edit(CFMENavigateStep):
    VIEW = MethodEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Method')


@navigator.register(Method)
class Copy(CFMENavigateStep):
    VIEW = MethodCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Copy this Method')
