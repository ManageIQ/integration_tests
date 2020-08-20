from copy import copy

import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import ParametrizedLocator
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import ClickableMixin
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Select
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import Button

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
from cfme.utils.timeutil import parsetime
from cfme.utils.wait import wait_for
from widgetastic_manageiq import EntryPoint
from widgetastic_manageiq import Input
from widgetastic_manageiq import ScriptBox
from widgetastic_manageiq import SummaryFormItem


class Inputs(View, ClickableMixin):
    ROOT = './/button[@id="exp_collapse_img"]/i'
    INDIRECT = True  # TODO: This appear to upset the parent lookup combined with ParView

    @property
    def is_opened(self):
        return 'fa-angle-up' in self.browser.classes(self)

    def child_widget_accessed(self, widget):
        if not self.is_opened:
            self.click()

    @ParametrizedView.nested
    class inputs(ParametrizedView):  # noqa
        PARAMETERS = ('name', )
        ROOT = ParametrizedLocator('//tr[./td[2]/input[normalize-space(@value)={name|quote}]]')
        ALL_FIELDS = '//div[@id="inputs_div"]/table//tr/td[2]/input'

        @cached_property
        def row_id(self):
            attr = self.browser.get_attribute(
                'id',
                './/td/input[contains(@id, "fields_name_")]',
                parent=self)
            return int(attr.rsplit('_', 1)[-1])

        name = Input(locator=ParametrizedLocator(
            './/td/input[contains(@id, "fields_name_{@row_id}")]'))
        data_type = Select(locator=ParametrizedLocator(
            './/td/select[contains(@id, "fields_datatype_{@row_id}")]'))
        default_value = Input(locator=ParametrizedLocator(
            './/td/input[contains(@id, "fields_value_{@row_id}")]'))

        @classmethod
        def all(cls, browser):
            results = []
            for e in browser.elements(cls.ALL_FIELDS):
                results.append((browser.get_attribute('value', e), ))
            return results

        def delete(self):
            xpath = './/a/i[contains(@class, "pficon-delete")]'
            self.browser.click(xpath, parent=self)
            try:
                del self.row_id
            except AttributeError:
                pass

    add_field = Text('//*[@id="inputs_div"]//i[contains(@class, "fa-plus")]')
    name = Input(locator='.//td/input[contains(@id, "field_name")]')
    data_type = Select(locator='.//td/select[contains(@id, "field_datatype")]')
    default_value = Input(locator='.//td/input[contains(@id, "field_default_value")]')
    finish_add_field = Text('//a[@title="Add this entry"]')

    def read(self):
        return self.inputs.read()

    def fill(self, value):
        keys = set(value.keys())
        value = copy(value)

        present = set(self.inputs.read().keys())
        to_delete = present - keys
        changed = False

        # Create the new ones
        for key in keys:
            if key not in present:
                new_value = value.pop(key)
                new_value['name'] = key
                self.add_field.wait_displayed()
                self.add_field.click()
                super().fill(new_value)
                self.finish_add_field.click()
                changed = True

        # Fill the rest as expected
        if self.inputs.fill(value):
            changed = True

        # delete unneeded
        for key in to_delete:
            self.inputs(name=key).delete()
            changed = True

        return changed


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
    inputs = Table(locator='#params_grid', assoc_column='Input Name')
    script = ScriptBox()
    embedded_method_table = Table(
        "//*[@id='embedded_methods_div']/table[contains(@class, 'table')]"
    )

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text.startswith('Automate Method [{}'.format(
                self.context['object'].display_name or self.context['object'].name)) and
            self.fqdn.is_displayed and
            # We check namespace separately as in tree there is status included
            self.fqdn.text[0] in self.context['object'].tree_path_name_only[1] and
            # We need to chop off the leading Domain name and namespace(cheecked in previous line)
            self.fqdn.text[1:] == self.context['object'].tree_path_name_only[2:])


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
    fill_strategy = WaitFillViewStrategy()
    title = Text('#explorer_title_text')

    location = BootstrapSelect('cls_method_location', can_hide_on_select=True)

    inline_name = Input(name='cls_method_name')
    inline_display_name = Input(name='cls_method_display_name')
    script = ScriptBox()
    data = Input(name='cls_method_data')
    validate_button = Button('Validate')
    inputs = View.nested(Inputs)

    playbook_name = Input(name='name')
    playbook_display_name = Input(name='display_name')
    repository = PlaybookBootstrapSelect('provisioning_repository_id')
    playbook = PlaybookBootstrapSelect('provisioning_playbook_id')
    machine_credential = PlaybookBootstrapSelect('provisioning_machine_credential_id')
    hosts = Input('provisioning_inventory')
    max_ttl = Input('provisioning_execution_ttl')
    logging_output = PlaybookBootstrapSelect('provisioning_log_output')
    escalate_privilege = BootstrapSwitch('provisioning_become_enabled')
    verbosity = PlaybookBootstrapSelect('provisioning_verbosity')
    playbook_input_parameters = PlaybookInputParameters()

    # Add embedded method
    embedded_method_table = Table('//*[@id="embedded_methods_div"]/table')
    embedded_method = EntryPoint(locator='//*[@id="automate-inline-method-select"]//button',
                                 tree_id="treeview-entrypoint_selection")

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
    inputs = View.nested(Inputs)

    # playbook
    playbook_name = Input(name='name')
    playbook_display_name = Input(name='display_name')
    repository = PlaybookBootstrapSelect('provisioning_repository_id')
    playbook = PlaybookBootstrapSelect('provisioning_playbook_id')
    machine_credential = PlaybookBootstrapSelect('provisioning_machine_credential_id')
    hosts = Input('provisioning_inventory')
    max_ttl = Input('provisioning_execution_ttl')
    logging_output = PlaybookBootstrapSelect('provisioning_log_output')
    escalate_privilege = BootstrapSwitch('provisioning_become_enabled')
    verbosity = PlaybookBootstrapSelect('provisioning_verbosity')
    playbook_input_parameters = PlaybookInputParameters()

    # Edit embedded method
    embedded_method_table = Table('//*[@id="embedded_methods_div"]/table')
    embedded_method = EntryPoint(locator='//*[@id="automate-inline-method-select"]//button',
                                 tree_id="treeview-entrypoint_selection")

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    def before_fill(self, values):
        location = self.context['object'].location.lower()
        if 'display_name' in values and location in ['inline', 'playbook']:
            values[f'{location}_display_name'] = values['display_name']
            del values['display_name']
        elif 'name' in values and location in ['inline', 'playbook']:
            values[f'{location}_name'] = values['name']
            del values['name']

    @property
    def is_displayed(self):
        return (
            self.in_explorer
            and self.datastore.is_opened
            and (f'Editing Automate Method "{self.context["object"].name}"' in self.title.text)
            and check_tree_path(
                self.datastore.tree.currently_selected,
                self.context["object"].tree_path,
                partial=True,
            )
        )


class Method(BaseEntity, Copiable):

    def __init__(self, collection, name=None, display_name=None, location='inline', script=None,
                 data=None, repository=None, playbook=None, machine_credential=None, hosts=None,
                 max_ttl=None, logging_output=None, escalate_privilege=None, verbosity=None,
                 playbook_input_parameters=None, cancel=False, validate=True, inputs=None,
                 embedded_method=None):
        super().__init__(collection)

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
        self.logging_output = logging_output
        self.escalate_privilege = escalate_privilege
        self.verbosity = verbosity
        self.playbook_input_parameters = playbook_input_parameters
        self.inputs = inputs
        self.embedded_method = embedded_method

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
            raise ItemNotFound(f'Method named {self.name} not found in the database')

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
        icon_name_map = {'inline': 'fa-ruby', 'playbook': 'vendor-ansible'}
        if self.display_name:
            return self.parent_obj.tree_path + [
                (icon_name_map[self.location.lower()], '{} ({})'.format(self.display_name,
                                                                        self.name))]
        else:
            return self.parent_obj.tree_path + [(icon_name_map[self.location.lower()], self.name)]

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
        view = self.create_view(MethodDetailsView, override=updates, wait='10s')
        view.wait_displayed()
        view.flash.assert_no_error()

    def delete(self, cancel=False):
        details_page = navigate_to(self, 'Details')
        details_page.configuration.item_select('Remove this Method', handle_alert=not cancel)
        if cancel:
            assert details_page.is_displayed
            details_page.flash.assert_no_error()
        else:
            result_view = self.create_view(ClassDetailsView, self.parent_obj, wait='10s')
            result_view.flash.assert_no_error()
            result_view.flash.assert_message(
                f'Automate Method "{self.name}": Delete successful')


@attr.s
class MethodCollection(BaseCollection):

    ENTITY = Method

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(
            self, name=None, display_name=None, location='inline', script=None, data=None,
            cancel=False, validate=True, repository=None, playbook=None, machine_credential=None,
            hosts=None, max_ttl=5, logging_output=None, escalate_privilege=None, verbosity=None,
            playbook_input_parameters=None, inputs=None, embedded_method=None):

        add_page = navigate_to(self, 'Add')

        location = location.capitalize()

        add_page.fill({'location': location})
        if location.lower() == 'inline':
            add_page.fill({
                'inline_name': name,
                'inline_display_name': display_name,
                'script': script,
                'data': data,
                'inputs': inputs,
                'embedded_method': embedded_method
            })
        if location.lower() == 'playbook':
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
                'logging_output': logging_output,
                'escalate_privilege': escalate_privilege,
                'verbosity': verbosity,
                'playbook_input_parameters': playbook_input_parameters
            })
            validate = False
        if validate:
            add_page.validate_button.click()
            add_page.wait_displayed()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Data validated successfully')
        if cancel:
            add_page.cancel_button.click()
            add_page.flash.assert_no_error()
            add_page.flash.assert_message('Add of new Automate Method was cancelled by the user',
                                          wait=3)
            return None
        else:
            add_page.add_button.click()
            add_page.flash.assert_no_error()

            # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
            if BZ(1704439).blocks:
                view = self.create_view(ClassDetailsView)
                view.flash.assert_message(f'Automate Method "{name}" was added')
                self.browser.refresh()

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
                logging_output=logging_output,
                escalate_privilege=escalate_privilege,
                verbosity=verbosity,
                playbook_input_parameters=playbook_input_parameters,
                inputs=inputs)

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
                f'Automate Method "{method.name}": Delete successful')

        # TODO(BZ-1704439): Remove the work-around once this BZ got fixed
        if BZ(1704439).blocks:
            self.browser.refresh()


@navigator.register(MethodCollection)
class Add(CFMENavigateStep):
    VIEW = MethodAddView
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.methods.select()
        self.prerequisite_view.configuration.item_select('Add a New Method')


@navigator.register(Method)
class Details(CFMENavigateStep):
    VIEW = MethodDetailsView
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self, *args, **kwargs):
        self.prerequisite_view.datastore.tree.click_path(*self.obj.tree_path)


@navigator.register(Method)
class Edit(CFMENavigateStep):
    VIEW = MethodEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit this Method')


@navigator.register(Method)
class Copy(CFMENavigateStep):
    VIEW = MethodCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Copy this Method')
