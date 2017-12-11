# -*- coding: utf-8 -*-
import attr

from cached_property import cached_property
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import Table, Text, View
from widgetastic_manageiq import SummaryFormItem, ScriptBox, Input
from widgetastic_patternfly import BootstrapSelect, BootstrapSwitch, Button, CandidateNotFound

from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.timeutil import parsetime
from cfme.utils.version import Version
from cfme.utils.wait import wait_for

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


class PlaybookBootstrapSelect(BootstrapSelect):
    """BootstrapSelect widget for Ansible Playbook Method form.

    BootstrapSelect widgets don't have ``data-id`` attribute in this form, so we have to override
    ROOT locator.

    """
    ROOT = ParametrizedLocator('.//select[normalize-space(@name)={@id|quote}]/..')


class ActionsCell(View):
    edit = Button(**{"ng-click": "vm.editKeyValue(this.arr[0], this.arr[1], this.arr[2], $index)"})
    delete = Button(**{"ng-click": "vm.removeKeyValue($index)"})


class PlaybookInputParameters(View):
    """Represents input parameters part of playbook method edit form.

    """

    input_name = Input(name="provisioning_key")
    default_value = Input(name="provisioning_value")
    provisioning_type = PlaybookBootstrapSelect("provisioning_type")
    add_button = Button(**{"ng-click": "vm.addKeyValue()"})
    variables_table = Table(
        ".//div[@id='inputs_div']//table",
        column_widgets={"Actions": ActionsCell()}
    )

    def _values_to_remove(self, values):
        return list(set(self.all_vars) - set(values))

    def _values_to_add(self, values):
        return list(set(values) - set(self.all_vars))

    def fill(self, values):
        """

        Args:
            values (list): [] to remove all vars or [("var", "value", "type"), ...] to fill the view
        """
        if set(values) == set(self.all_vars):
            return False
        else:
            for value in self._values_to_remove(values):
                rows = list(self.variables_table)
                for row in rows:
                    if row[0].text == value[0]:
                        row["Actions"].widget.delete.click()
                        break
            for value in self._values_to_add(values):
                self.input_name.fill(value[0])
                self.default_value.fill(value[1])
                self.provisioning_type.fill(value[2])
                self.add_button.click()
            return True

    @property
    def all_vars(self):
        if self.variables_table.is_displayed:
            return [(row["Input Name"].text, row["Default value"].text, row["Data Type"].text) for
                    row in self.variables_table]
        else:
            return []

    def read(self):
        return self.all_vars


class MethodAddView(AutomateExplorerView):
    title = Text('#explorer_title_text')

    location = BootstrapSelect('cls_method_location', can_hide_on_select=True)

    inline_name = Input(name='cls_method_name')
    inline_display_name = Input(name='cls_method_display_name')
    script = ScriptBox()
    data = Input(name='cls_method_data')
    validate_button = Button('Validate')
    # TODO: inline input parameters

    playbook_name = Input(name='name')
    playbook_display_name = Input(name='display_name')
    repository = PlaybookBootstrapSelect('provisioning_repository_id')
    playbook = PlaybookBootstrapSelect('provisioning_playbook_id')
    machine_credential = PlaybookBootstrapSelect('provisioning_machine_credential_id')
    hosts = Input('provisioning_inventory')
    max_ttl = Input('provisioning_execution_ttl')
    escalate_privilege = BootstrapSwitch('provisioning_become_enabled')
    verbosity = PlaybookBootstrapSelect('provisioning_verbosity')
    playbook_input_parameters = PlaybookInputParameters()

    add_button = Button('Add')
    cancel_button = Button('Cancel')

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

    # inline
    inline_name = Input(name='method_name')
    inline_display_name = Input(name='method_display_name')
    script = ScriptBox()
    data = Input(name='method_data')
    validate_button = Button('Validate')
    # TODO: inline input parameters

    # playbook
    playbook_name = Input(name='name')
    playbook_display_name = Input(name='display_name')
    repository = PlaybookBootstrapSelect('provisioning_repository_id')
    playbook = PlaybookBootstrapSelect('provisioning_playbook_id')
    machine_credential = PlaybookBootstrapSelect('provisioning_machine_credential_id')
    hosts = Input('provisioning_inventory')
    max_ttl = Input('provisioning_execution_ttl')
    escalate_privilege = BootstrapSwitch('provisioning_become_enabled')
    verbosity = PlaybookBootstrapSelect('provisioning_verbosity')
    playbook_input_parameters = PlaybookInputParameters()

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    def before_fill(self, values):
        location = self.context['object'].location
        if 'display_name' in values and location in ['inline', 'playbook']:
            values['{}_display_name'.format(location)] = values['display_name']
            del values['display_name']
        elif 'name' in values and location in ['inline', 'playbook']:
            values['{}_name'.format(location)] = values['name']
            del values['name']

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

    def __init__(self, collection, name=None, display_name=None, location='inline', script=None,
                 data=None, repository=None, playbook=None, machine_credential=None, hosts=None,
                 max_ttl=None, escalate_privilege=None, verbosity=None,
                 playbook_input_parameters=None, cancel=False, validate=True):
        super(Method, self).__init__(collection)

        self.name = name
        if display_name is not None:
            self.display_name = display_name
        self.location = location
        self.script = script
        self.data = data
        self.repository = repository
        self.playbook = playbook
        self.machine_credential = machine_credential
        self.hosts = hosts
        self.max_ttl = max_ttl
        self.escalate_privilege = escalate_privilege
        self.verbosity = verbosity
        self.playbook_input_parameters = playbook_input_parameters

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
        if self.appliance.version < '5.9':
            icon_name_map = {'inline': 'product-method'}
        else:
            icon_name_map = {'inline': 'fa-ruby', 'playbook': 'vendor-ansible'}
        if self.display_name:
            return self.parent_obj.tree_path + [
                (icon_name_map[self.location], '{} ({})'.format(self.display_name, self.name))]
        else:
            return self.parent_obj.tree_path + [(icon_name_map[self.location], self.name)]

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
            cancel=False, validate=True, repository=None, playbook=None, machine_credential=None,
            hosts=None, max_ttl=None, escalate_privilege=None, verbosity=None,
            playbook_input_parameters=None):
        add_page = navigate_to(self, 'Add', wait_for_view=True)
        add_page.fill({'location': location})
        if location == 'inline':
            add_page.fill({
                'inline_name': name,
                'inline_display_name': display_name,
                'script': script,
                'data': data
            })
        if location == 'playbook':
            add_page.fill({
                'playbook_name': name,
                'playbook_display_name': display_name,
                'repository': repository
            })
            wait_for(lambda: add_page.playbook.is_displayed, delay=0.5, num_sec=2)
            add_page.fill({
                'playbook': playbook,
                'machine_credential': machine_credential,
                'hosts': hosts,
                'max_ttl': max_ttl,
                'escalate_privilege': escalate_privilege,
                'verbosity': verbosity,
                'playbook_input_parameters': playbook_input_parameters
            })
            validate = False
        if validate and not BZ(1499881, forced_streams=['5.9']).blocks:
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
            msg = 'Automate Method "{}" was added'.format(name)
            add_page.flash.assert_success_message(msg)
            return self.instantiate(
                name=name,
                display_name=display_name,
                location=location,
                script=script,
                data=data,
                repository=repository,
                playbook=playbook,
                machine_credential=machine_credential,
                hosts=hosts,
                max_ttl=max_ttl,
                escalate_privilege=escalate_privilege,
                verbosity=verbosity,
                playbook_input_parameters=playbook_input_parameters)

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
