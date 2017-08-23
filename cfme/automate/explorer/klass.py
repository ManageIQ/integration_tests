# -*- coding: utf-8 -*-
import re
from cached_property import cached_property
from copy import copy

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import ParametrizedLocator, ParametrizedString
from widgetastic.widget import Checkbox, Text, ParametrizedView
from widgetastic_manageiq import Table
from widgetastic_patternfly import BootstrapSelect, CandidateNotFound, Input, Button, Tab

from cfme.exceptions import ItemNotFound
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

from . import AutomateExplorerView, check_tree_path
from .common import Copiable, CopyViewBase
from .namespace import NamespaceDetailsView


class ClassCopyView(AutomateExplorerView, CopyViewBase):
    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Copy Automate Class' and
            self.datastore.is_opened and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path))


class ClassDetailsView(AutomateExplorerView):
    title = Text('#explorer_title_text')

    class instances(Tab):  # noqa
        table = Table('#class_instances_grid')

    class methods(Tab):  # noqa
        table = Table('#class_methods_grid')

    class properties(Tab):  # noqa
        table = Table('//table[./preceding-sibling::h3[normalize-space(.)="Properties"]][1]')
        overrides = Table(
            '//table[./preceding-sibling::h3[normalize-space(.)="Domain Overrides (by priority)"]]')

    class schema(Tab):  # noqa
        schema_title = Text('//div[@id="class_fields_div"]/h3')
        table = Table('//div[@id="class_fields_div"]/table')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Automate Class "{}"'.format(
                self.context['object'].display_name or self.context['object'].name) and
            self.datastore.is_opened and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path))


class ClassForm(AutomateExplorerView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    display_name = Input(name='display_name')
    description = Input(name='description')

    cancel_button = Button('Cancel')


class ClassAddView(ClassForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Datastore' and
            self.datastore.is_opened and
            self.title.text == 'Adding a new Class')


class ClassEditView(ClassForm):
    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Editing Class "{}"'.format(self.obj.name))


class ClassCollection(Navigatable):
    def __init__(self, parent_namespace):
        self.parent = parent_namespace
        Navigatable.__init__(self, appliance=parent_namespace.appliance)

    @property
    def tree_path(self):
        return self.parent.tree_path

    def instantiate(self, name=None, display_name=None, description=None):
        return Class(self, name=name, display_name=display_name, description=description)

    def create(self, name=None, display_name=None, description=None, cancel=False):
        add_page = navigate_to(self, 'Add')
        fill_dict = {
            k: v
            for k, v in {
                'name': name, 'display_name': display_name, 'description': description
            }.items()
            if v is not None}
        add_page.fill(fill_dict)
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Class was cancelled by the user')
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message(
                'Automate Class "/{}/{}" was added'.format(
                    '/'.join(self.tree_path[1:]), name))
            return self.instantiate(name=name, display_name=display_name, description=description)

    def delete(self, *classes):
        all_page = navigate_to(self.parent, 'Details')
        classes = list(classes)
        parents = set()
        # Check if the parent is the same
        for klass in classes:
            parents.add(klass.parent)
        if len(parents) > 1:
            raise ValueError('You passed classes that are not under one parent.')

        checked_classes = []
        if not all_page.namespaces.is_displayed:
            raise ValueError('No class found!')
        all_page.namespaces.uncheck_all()
        for row in all_page.namespaces.rows(_row__attr_startswith=('data-click-id', 'aec-')):
            name = row[2].text
            for klass in classes:
                if (klass.display_name and klass.display_name == name) or klass.name == name:
                    checked_classes.append(klass)
                    row[0].check()
                    break

            if set(classes) == set(classes):
                break

        if set(classes) != set(checked_classes):
            raise ValueError('Some of the classes were not found in the UI.')

        all_page.configuration.item_select('Remove selected Items', handle_alert=True)
        all_page.flash.assert_no_error()
        for klass in checked_classes:
            all_page.flash.assert_message(
                'Automate Class "{}": Delete successful'.format(klass.description or klass.name))


@navigator.register(ClassCollection)
class Add(CFMENavigateStep):
    VIEW = ClassAddView
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a New Class')


class Class(Navigatable, Copiable):
    def __init__(self, collection, name, display_name, description):
        Navigatable.__init__(self, appliance=collection.appliance)
        self.collection = collection
        self.name = name
        if display_name is not None:
            self.display_name = display_name
        if description is not None:
            self.description = description

    @cached_property
    def display_name(self):
        return self.db_object.display_name

    @cached_property
    def description(self):
        return self.db_object.description

    @cached_property
    def db_id(self):
        table = self.appliance.db.client['miq_ae_classes']
        try:
            return self.appliance.db.client.session.query(table.id).filter(
                table.name == self.name,
                table.namespace_id == self.namespace.db_id)[0]  # noqa
        except IndexError:
            raise ItemNotFound('Class named {} not found in the database'.format(self.name))

    @property
    def db_object(self):
        table = self.appliance.db.client['miq_ae_classes']
        return self.appliance.db.client.session.query(table).filter(table.id == self.db_id).first()

    @property
    def parent(self):
        return self.collection.parent

    @property
    def namespace(self):
        return self.parent

    @property
    def domain(self):
        return self.parent.domain

    @property
    def tree_path(self):
        if self.display_name:
            return self.parent.tree_path + ['{} ({})'.format(self.display_name, self.name)]
        else:
            return self.parent.tree_path + [self.name]

    @property
    def tree_path_name_only(self):
        return self.parent.tree_path + [self.name]

    @property
    def pure_tree_path(self):
        return self.parent.tree_path[1:] + [self.name]

    @property
    def fqdn(self):
        return '/' + '/'.join(self.pure_tree_path)

    @cached_property
    def instances(self):
        from .instance import InstanceCollection
        return InstanceCollection(self)

    @cached_property
    def methods(self):
        from .method import MethodCollection
        return MethodCollection(self)

    @cached_property
    def schema(self):
        return ClassSchema(self)

    def delete(self, cancel=False):
        # Ensure this has correct data
        self.description
        # Do it!
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Remove this Class', handle_alert=not cancel)
        if cancel:
            assert details_page.is_displayed
            details_page.flash.assert_no_error()
        else:
            result_view = self.create_view(NamespaceDetailsView, self.parent)
            assert result_view.is_displayed
            result_view.flash.assert_no_error()
            result_view.flash.assert_message(
                'Automate Class "{}": Delete successful'.format(self.description or self.name))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(ClassDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            # When updating, class FQDN is used
            if 'name' in updates:
                # Replace the last component with a new name
                fqdn = self.fqdn.rsplit('/', 1)[0] + '/{}'.format(updates['name'])
            else:
                fqdn = self.fqdn
            view.flash.assert_message('Automate Class "{}" was saved'.format(fqdn))
        else:
            view.flash.assert_message(
                'Edit of Automate Class "{}" was cancelled by the user'.format(self.name))

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


@navigator.register(Class)
class Details(CFMENavigateStep):
    VIEW = ClassDetailsView
    prerequisite = NavigateToAttribute('domain', 'Details')

    def step(self):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(Class)
class Edit(CFMENavigateStep):
    VIEW = ClassEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Class')


@navigator.register(Class)
class Copy(CFMENavigateStep):
    VIEW = ClassCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Copy this Class')


# schema
class ClassSchemaEditView(ClassDetailsView):
    class schema(Tab):  # noqa
        schema_title = Text('//div[@id="form_div"]/h3')

        @ParametrizedView.nested
        class fields(ParametrizedView):  # noqa
            PARAMETERS = ('name', )
            # Points to the <tr>
            ROOT = ParametrizedLocator(
                './/input[starts-with(@id, "fields_name_") and @value={name|quote}]/../..')
            ALL_FIELDS = './/input[starts-with(@name, "fields_name_")]'

            @cached_property
            def row_id(self):
                attr = self.browser.get_attribute(
                    'id',
                    './td/input[starts-with(@id, "fields_name_")',
                    parent=self)
                return int(attr.rsplit('_', 1)[-1])

            name = Input(name=ParametrizedString('fields_name_{@row_id}'))
            type = BootstrapSelect(ParametrizedString('fields_aetype_{@row_id}'))
            data_type = BootstrapSelect(ParametrizedString('fields_datatype_{@row_id}'))
            default_value = Input(name=ParametrizedString('fields_default_value_{@row_id}'))
            display_name = Input(name=ParametrizedString('fields_display_name_{@row_id}'))
            description = Input(name=ParametrizedString('fields_description_{@row_id}'))
            substitute = Checkbox(name=ParametrizedString('fields_substitute_{@row_id}'))
            collect = Input(name=ParametrizedString('fields_collect_{@row_id}'))
            message = Input(name=ParametrizedString('fields_message_{@row_id}'))
            on_entry = Input(name=ParametrizedString('fields_on_entry_{@row_id}'))
            on_exit = Input(name=ParametrizedString('fields_on_exit_{@row_id}'))
            on_error = Input(name=ParametrizedString('fields_on_error_{@row_id}'))
            max_retries = Input(name=ParametrizedString('fields_max_retries_{@row_id}'))
            max_time = Input(name=ParametrizedString('fields_max_time_{@row_id}'))

            def delete(self):
                self.browser.click(
                    './/img[@alt="Click to delete this field from schema"]', parent=self)
                try:
                    del self.row_id
                except AttributeError:
                    pass

            @classmethod
            def all(cls, browser):
                result = []
                for e in browser.elements(cls.ALL_FIELDS):
                    result.append((browser.get_attribute('value', e), ))
                return result

        add_field = Text('//img[@alt="Equal green"]')
        name = Input(name='field_name')
        type = BootstrapSelect('field_aetype')
        data_type = BootstrapSelect('field_datatype')
        default_value = Input(name='field_default_value')
        display_name = Input(name='field_display_name')
        description = Input(name='field_description')
        substitute = Checkbox(name='field_substitute')
        collect = Input(name='field_collect')
        message = Input(name='field_message')
        on_entry = Input(name='field_on_entry')
        on_exit = Input(name='field_on_exit')
        on_error = Input(name='field_on_error')
        max_retries = Input(name='field_max_retries')
        max_time = Input(name='field_max_time')
        finish_add_field = Text('//img[@alt="Add this entry"]')

        save_button = Button('Save')
        reset_button = Button('Reset')
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.schema.is_active and
            self.schema.schema_title.is_displayed and
            self.schema.schema_title.text == 'Schema' and
            (self.schema.add_field.is_displayed or self.schema.finish_add_field.is_displayed))


class ClassSchema(Navigatable):
    FIELD_NAMES = [
        'name', 'type', 'data_type', 'default_value', 'display_name', 'description', 'substitute',
        'collect', 'message', 'on_entry', 'on_exit', 'on_error', 'max_retries', 'max_time']

    def __init__(self, klass):
        Navigatable.__init__(self, appliance=klass.appliance)
        self.klass = klass

    @property
    def schema_field_names(self):
        page = navigate_to(self.klass, 'Details')
        page.schema.select()
        fields = []
        for row in page.schema.table:
            fields.append(re.sub(r'^\(([^)]+)\)$', '\\1', row.name.text.strip()))
        return fields

    def _fill_field(
            self, page, **fields):
        page.schema.add_field.click()
        # Collect things to one fill dict
        fields = copy(fields)
        fill_dict = {}
        for field_name in self.FIELD_NAMES:
            try:
                fill_dict[field_name] = fields.pop(field_name)
            except KeyError:
                continue

        if fields:
            raise TypeError(
                'Unexpected fields passed to schema: {}'.format(', '.join(fields.keys())))

        result = page.schema.fill(fill_dict)

        page.schema.finish_add_field.click()
        page.flash.assert_no_error()

        return result

    def add_field(self, **kwargs):
        page = navigate_to(self, 'Edit')
        change = self._fill_field(page, **kwargs)
        if change:
            page.schema.save_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Schema for Automate Class "{}" was saved'.format(self.klass.name))
        else:
            page.schema.cancel_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Edit of schema for Automate Class "{}" was cancelled by the user'.format(
                    self.klass.name))

    def add_fields(self, *fields):
        page = navigate_to(self, 'Edit')
        change = False
        for field in fields:
            if self._fill_field(page, **field):
                change = True
        if change:
            page.schema.save_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Schema for Automate Class "{}" was saved'.format(self.klass.name))
        else:
            page.schema.cancel_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Edit of schema for Automate Class "{}" was cancelled by the user'.format(
                    self.klass.name))

    def _delete_field(
            self, page, field):
        page.schema.fields(field).delete()

        page.flash.assert_no_error()

        return True

    def delete_field(self, field):
        page = navigate_to(self, 'Edit')
        change = self._delete_field(page, field)
        if change:
            page.schema.save_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Schema for Automate Class "{}" was saved'.format(self.klass.name))
        else:
            page.schema.cancel_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Edit of schema for Automate Class "{}" was cancelled by the user'.format(
                    self.klass.name))

    def delete_fields(self, *fields):
        page = navigate_to(self, 'Edit')
        change = False
        for field in fields:
            if self._delete_field(page, field):
                change = True
        if change:
            page.schema.save_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Schema for Automate Class "{}" was saved'.format(self.klass.name))
        else:
            page.schema.cancel_button.click()
            page.flash.assert_no_error()
            page.flash.assert_message(
                'Edit of schema for Automate Class "{}" was cancelled by the user'.format(
                    self.klass.name))


@navigator.register(ClassSchema, 'Edit')
class EditSchema(CFMENavigateStep):
    VIEW = ClassSchemaEditView
    prerequisite = NavigateToAttribute('klass', 'Details')

    def step(self):
        self.prerequisite_view.schema.select()
        self.prerequisite_view.configuration.item_select('Edit selected Schema')
