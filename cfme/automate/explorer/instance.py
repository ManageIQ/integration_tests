import re

import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import ParametrizedLocator
from widgetastic.utils import ParametrizedString
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.automate.explorer import AutomateExplorerView
from cfme.automate.explorer import check_tree_path
from cfme.automate.explorer.common import Copiable
from cfme.automate.explorer.common import CopyViewBase
from cfme.automate.explorer.klass import ClassDetailsView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from widgetastic_manageiq import Table


class InstanceCopyView(AutomateExplorerView, CopyViewBase):
    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Copy Automate Instance' and
            self.datastore.is_opened and
            check_tree_path(
                self.datastore.tree.currently_selected,
                self.context['object'].tree_path))


class InstanceDetailsView(AutomateExplorerView):
    title = Text('#explorer_title_text')
    table = Table('#instance_fields_grid')
    domain_priority = Text('//*[@id="instances"]/table/tbody')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text.startswith('Automate Instance [{}'.format(
                self.context['object'].display_name or self.context['object'].name)) and
            self.datastore.is_opened and (BZ(1704439).blocks or check_tree_path(
                self.datastore.tree.currently_selected, self.context["object"].tree_path))
        )


class InstanceAddView(AutomateExplorerView):
    title = Text('#explorer_title_text')

    name = Input(name='cls_inst_name')
    display_name = Input(name='cls_inst_display_name')
    description = Input(name='cls_inst_description')

    @ParametrizedView.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ('name', )
        ROOT = ParametrizedLocator('.//tr[./td[1][contains(normalize-space(.), "({name})")]]')
        ALL_FIELDS = './/table//tr/td[1]'

        @cached_property
        def row_id(self):
            attr = self.browser.get_attribute(
                'id',
                './td/input[starts-with(@id, "cls_inst_value_")]',
                parent=self)
            return int(attr.rsplit('_', 1)[-1])

        value = Input(name=ParametrizedString('cls_inst_value_{@row_id}'))
        on_entry = Input(name=ParametrizedString('cls_inst_on_entry_{@row_id}'))
        on_exit = Input(name=ParametrizedString('cls_inst_on_exit_{@row_id}'))
        on_error = Input(name=ParametrizedString('cls_inst_on_error_{@row_id}'))
        collect = Input(name=ParametrizedString('cls_inst_collect_{@row_id}'))

        @classmethod
        def all(cls, browser):
            results = []
            for e in browser.elements(cls.ALL_FIELDS):
                text = re.sub(r'^\(|\)$', '', browser.text(e))
                results.append((text, ))
            return results

    add_button = Button('Add')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.datastore.is_opened and
            self.title.text == 'Adding a new Automate Instance')


class InstanceEditView(AutomateExplorerView):
    title = Text('#explorer_title_text')

    name = Input(name='inst_name')
    display_name = Input(name='inst_display_name')
    description = Input(name='inst_description')

    @ParametrizedView.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ('name', )
        ROOT = ParametrizedLocator('//h3[normalize-space(.)="Fields"]'
                                   '/following-sibling::table'
                                   '//tr[./td[1][contains(normalize-space(.), "({name})")]]')
        ALL_FIELDS = './/table//tr/td[1]'

        @cached_property
        def row_id(self):
            attr = self.browser.get_attribute(
                'id',
                './td/input[starts-with(@id, "inst_value_")]',
                parent=self)
            return int(attr.rsplit('_', 1)[-1])

        value = Input(name=ParametrizedString('inst_value_{@row_id}'))
        on_entry = Input(name=ParametrizedString('inst_on_entry_{@row_id}'))
        on_exit = Input(name=ParametrizedString('inst_on_exit_{@row_id}'))
        on_error = Input(name=ParametrizedString('inst_on_error_{@row_id}'))
        collect = Input(name=ParametrizedString('inst_collect_{@row_id}'))

        @classmethod
        def all(cls, browser):
            results = []
            for e in browser.elements(cls.ALL_FIELDS):
                text = re.sub(r'^\(|\)$', '', browser.text(e))
                results.append((text, ))
            return results

    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Editing Automate Instance "{}"'
                               .format(self.context['object'].name)
        )


class Instance(BaseEntity, Copiable):
    ICON_NAME = 'fa-file-text-o'

    def __init__(self, collection, name, display_name=None, description=None, fields=None):
        super(Instance, self).__init__(collection)

        self.name = name
        if display_name is not None:
            self.display_name = display_name
        if description is not None:
            self.description = description
        self.fields = fields

    __repr__ = object.__repr__

    @cached_property
    def display_name(self):
        return self.db_object.display_name

    @cached_property
    def description(self):
        return self.db_object.description

    @cached_property
    def db_id(self):
        table = self.appliance.db.client['miq_ae_instances']
        try:
            return self.appliance.db.client.session.query(table.id).filter(
                table.name == self.name,
                table.class_id == self.klass.db_id)[0]  # noqa
        except IndexError:
            raise ItemNotFound('Instance named {} not found in the database'.format(self.name))

    @property
    def db_object(self):
        table = self.appliance.db.client['miq_ae_instances']
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
            return self.parent_obj.tree_path + [
                (self.ICON_NAME, '{} ({})'.format(self.display_name, self.name))]
        else:
            return self.parent_obj.tree_path + [(self.ICON_NAME, self.name)]

    @property
    def tree_path_name_only(self):
        return self.parent_obj.tree_path_name_only + [self.name]

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
        view = self.create_view(InstanceDetailsView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Automate Instance "{}" was saved'.format(updates.get('name', self.name)))
        else:
            view.flash.assert_message(
                'Edit of Automate Instance "{}" was cancelled by the user'.format(self.name))

    def delete(self, cancel=False):
        # Ensure this has correct data
        self.description
        # Do it!
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Remove this Instance', handle_alert=not cancel)
        if cancel:
            assert details_page.is_displayed
            details_page.flash.assert_no_error()
        else:
            result_view = self.create_view(ClassDetailsView, self.parent_obj)
            assert result_view.is_displayed
            result_view.flash.assert_no_error()
            result_view.flash.assert_message(
                'Automate Instance "{}": Delete successful'.format(self.description or self.name))

            # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
            if BZ(1704439).blocks:
                self.browser.refresh()


@attr.s
class InstanceCollection(BaseCollection):

    ENTITY = Instance

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, name=None, display_name=None, description=None, fields=None, cancel=False):
        add_page = navigate_to(self, 'Add')
        fill_dict = {
            k: v
            for k, v in {
                'name': name,
                'display_name': display_name,
                'description': description,
                'fields': fields,
            }.items()
            if v is not None
        }
        add_page.fill(fill_dict)
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Instance was cancelled by the user')
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Automate Instance "{}" was added'.format(name))

            # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
            if BZ(1704439).blocks:
                self.browser.refresh()

            return self.instantiate(
                name=name,
                display_name=display_name,
                description=description,
                fields=fields)

    def delete(self, *instances):
        all_page = navigate_to(self.parent, 'Details')
        all_page.instances.select()
        instances = list(instances)
        parents = set()
        for instance in instances:
            parents.add(instance.parent)
        if len(parents) > 1:
            raise ValueError('You passed instances that are not under one class.')

        checked_instances = []
        if not all_page.instances.table.is_displayed:
            raise ValueError('No instance found!')
        all_page.instances.table.uncheck_all()
        for row in all_page.instances.table:
            name = row[2].text
            for instance in instances:
                if (
                        (instance.display_name and instance.display_name == name) or
                        instance.name == name):
                    checked_instances.append(instance)
                    row[0].check()
                    break

            if set(instances) == set(checked_instances):
                break

        if set(instances) != set(checked_instances):
            raise ValueError('Some of the instances were not found in the UI.')

        all_page.configuration.item_select('Remove Instances', handle_alert=True)
        all_page.flash.assert_no_error()
        for instance in checked_instances:
            all_page.flash.assert_message(
                'Automate Instance "{}": Delete successful'.format(instance.name))

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if BZ(1704439).blocks:
            self.browser.refresh()


@navigator.register(InstanceCollection)
class Add(CFMENavigateStep):
    VIEW = InstanceAddView
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.instances.select()
        self.prerequisite_view.configuration.item_select('Add a New Instance')


@navigator.register(Instance)
class Details(CFMENavigateStep):
    VIEW = InstanceDetailsView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self, *args, **kwargs):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(Instance)
class Edit(CFMENavigateStep):
    VIEW = InstanceEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit this Instance')


@navigator.register(Instance)
class Copy(CFMENavigateStep):
    VIEW = InstanceCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Copy this Instance')
