from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import Parameter, VersionPick, Version
from widgetastic.widget import ParametrizedView, Table, Text, View, ParametrizedString, ParametrizedLocator, Widget
from widgetastic_patternfly import Input, BootstrapSelect, Dropdown, Button, CandidateNotFound, Tab

from cfme.base.login import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.services.myservice import MyService
from cfme.utils.appliance import current_appliance, MiqImplementationContext
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (Accordion, ManageIQTree, Calendar, SummaryTable,
                                  BaseNonInteractiveEntitiesView, ItemsToolBarViewSelector,
                                  BaseEntitiesView, DynamicTable, FileInput, ParametrizedSummaryTable, BootstrapSwitch, FonticonPicker)
from . import GenericObjectDefinition, GenericObjectDefinitionCollection


class GenericObjectDefinitionToolbar(View):
    """
    Represents provider toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    download = Dropdown(text='Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class GenericObjectDefinitionView(BaseLoggedInPage):

    def in_generic_object_definition(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Automation', 'Automate'])


class GenericObjectDefinitionAllView(GenericObjectDefinitionView):
    toolbar = View.nested(GenericObjectDefinitionToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition() and
            self.toolbar.configuration.is_displayed and
            self.entities.title.text == 'All Generic Object Classes'
        )


class ParametersForm(View):
    ROOT = ParametrizedLocator('//generic-object-table-component[@key-type="{@param_type}"]')
    ALL_PAREMETERS = './/input[contains(@class, "ng-not-empty")]'
    add = Button(ParametrizedString('Add {@param_type}'))
    name = Input(locator='.//input[contains(@class, "ng-empty")]')
    type_class = BootstrapSelect(
        locator='.//input[contains(@class, "ng-empty")]//ancestor::tr//button')

    def __init__(self, parent, param_type, logger=None):
        View.__init__(self, parent, logger=logger)
        self.param_type = param_type

    def all(self):
        return [(element.get_attribute('value'), element.get_attribute('name'))
                for element in self.browser.elements(self.ALL_PAREMETERS)]

    @property
    def empty_field_is_present(self):
        try:
            return self.browser.element(self.name)
        except Exception:
            return False

    def add_parameter_row(self):
        if not self.empty_field_is_present:
            self.add.click()

    def fill(self, parameters):
        if parameters:
            if isinstance(parameters, dict):
                for name, type_class in parameters.items():
                    self.add_parameter_row()
                    self.type_class.fill(type_class)
                    self.name.fill(name)
            elif isinstance(parameters, list):
                for name in parameters:
                    self.add_parameter_row()
                    self.name.fill(name)

    def delete(self, name):
        all_params = self.all()
        for param in all_params:
            param_name, element_name = param
            if param_name == name:
                self.browser.element(
                    '//td[contains(@ng-class,  "{}")]/ancestor::tr'
                    '//div[@title = "Delete Row"]'.format(element_name)).click()


class GenericObjectDefinitionAddEditView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')
    name = Input(id='generic_object_definition_name')
    description = Input(id='generic_object_definition_description')
    cancel = Button('Cancel')

    attributes = ParametersForm(param_type="Attribute")
    methods = ParametersForm(param_type="Method")
    associations = ParametersForm(param_type="Association")

    @View.nested
    class custom_image_file(View):    # noqa
        file = FileInput(name='generic_object_definition_image_file')
        upload_chosen_file = Button('Upload chosen File')


class GenericObjectDefinitionAddView(GenericObjectDefinitionAddEditView):

    add = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition and
            self.title.text == 'Add a new Generic Object Class'
        )


class GenericObjectDefinitionEditView(GenericObjectDefinitionAddEditView):

    save = Button('Save')
    reset = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition and
            self.title.text == 'Edit Generic Object Class'
        )


class GenericObjectDefinitionDetailsView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')
    configuration = Dropdown(text='Configuration')
    summary = ParametrizedSummaryTable()

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition and
            self.title.text == 'Generic Object Class {}'.format(self.context['object'].name)
        )


class GenericObjectDetailsView(BaseLoggedInPage):
    configuration = Dropdown(text='Configuration')
    summary = ParametrizedSummaryTable()


class GenericObjectButtonView(GenericObjectDefinitionView):

    button_type = BootstrapSelect(name='button_type')

    name = Input(name='name')
    description = Input(name='description')
    display = BootstrapSwitch(name='display')
    image = VersionPick({
        Version.lowest(): BootstrapSelect('button_image'),
        '5.9': FonticonPicker('button_icon')})
    dialog = BootstrapSelect(name='dialog')
    open_url = BootstrapSwitch(name='open_url')
    display_for = BootstrapSelect(name='display_for')
    submit_version = BootstrapSelect(name='submit_how')
    system_process = BootstrapSelect(name='ae_instance')
    system_message = Input(name='ae_message')
    request = Input(name='request')
    add_attribute_value_key = Button('Add Attribute/Value Pair')
    attribute_value_table = DynamicTable(
        '//generic-object-table-component[@add-row-text="Add Attribute/Value Pair"]//table',
        column_widgets={'Name': Input, 'Value': Input})
    role = BootstrapSelect(name='visibility')

    cancel = Button('Cancel')


class GenericObjectButtonGroupView(GenericObjectDefinitionView):
    name = Input(name='name')
    display = BootstrapSwitch(name='display')
    description = Input(name='description')
    image = VersionPick({
        Version.lowest(): BootstrapSelect('button_image'),
        '5.9': FonticonPicker('button_icon')})

    cancel = Button('Cancel')


@MiqImplementationContext.external_for(GenericObjectDefinitionCollection.create, ViaUI)
def create(self, name, description, attributes=None, associations=None, methods=None,
           custom_image_file_path=None, cancel=False):
    view = navigate_to(self, 'Add')
    view.fill({
        'name': name,
        'description': description
    })
    view.associations.fill(associations)
    view.attributes.fill(attributes)
    view.methods.fill(methods)
    if custom_image_file_path:
        view.custom_image_file.file.fill(custom_image_file_path)
        view.custom_image_file.upload_chosen_file.click()
    if cancel:
        view.cancel.click()
    else:
        view.add.click()
        view.flash.assert_no_error()

    entity = self.instantiate(
        name=name, description=description, attributes=attributes, associations=associations,
        methods=methods, custom_image_file_path=custom_image_file_path
    )
    return entity


@MiqImplementationContext.external_for(GenericObjectDefinition.update, ViaUI)
def update(self, updates, reset=False, cancel=False):
    view = navigate_to(self, 'Edit')
    view.fill({
        'name': updates.get('name'),
        'description': updates.get('description')
    })
    view.associations.fill(updates.get('associations'))
    view.attributes.fill(updates.get('attributes'))
    view.methods.fill(updates.get('methods'))
    if updates.get('custom_image_file_path'):
        view.custom_image_file.file.fill('custom_image_file_path')
        view.custom_image_file.upload_chosen_file.click()
    if reset:
        view.reset.click()
    if cancel:
        view.cancel.click()
    elif not reset and not cancel:
        view.save.click()
        view = self.create_view(GenericObjectDefinitionDetailsView, override=updates)
        view.flash.assert_no_error()


@MiqImplementationContext.external_for(GenericObjectDefinition.delete, ViaUI)
def delete(self):
    view = navigate_to(self, 'Details')

    view.configuration.item_select(
        'Remove this Generic Object Classes from Inventory', handle_alert=True)
    view = self.create_view(GenericObjectDefinitionAllView)
    view.flash.assert_no_error()
    assert view.is_displayed


@MiqImplementationContext.external_for(GenericObjectDefinition.add_button, ViaUI)
def add_button(self, name, description, image, request, button_type='Default', display=None,
               dialog=None, open_url=None, display_for=None, submit_version=None,
               system_message=None, attributes=None, role=None, button_group=None, cancel=False):
    view = navigate_to(self, 'Add Button', button_group=button_group)
    view.fill({
        'button_type': button_type,
        'name': name,
        'description': description,
        'display': display,
        'image': image,
        'dialog': dialog,
        'open_url':open_url,
        'display_for': display_for,
        'request': request,
        'submit_version': submit_version,
        'system_message': system_message
    })
    if attributes:
        for name, type in attributes.items():
            view.attribute_value_table.fill([{'Name': name}, {'Value': type}])
    if isinstance(role, dict):
        view.role.select('<By Role>')
        # todo select roles
    if cancel:
        view.cancel.click()
    else:
        view.add.click()
    view.flash.assert_no_error


@MiqImplementationContext.external_for(GenericObjectDefinition.add_button_group, ViaUI)
def add_button_group(self, name, description, image, display, cancel=False):
    view = navigate_to(self, 'Add Button Group')
    view.fill({
        'name': name,
        'display': display,
        'description': description,
        'image': image,
    })
    if cancel:
        view.cancel.click()
    else:
        view.add.click()
    view.flash.assert_no_error()


@MiqImplementationContext.external_for(GenericObjectDefinition.exists.getter, ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except CandidateNotFound:
        return False


@MiqImplementationContext.external_for(GenericObjectDefinition.generic_objects.getter, ViaUI)
def generic_objects(self):
    return self.collections.generic_objects


@navigator.register(GenericObjectDefinitionCollection, 'All')
class GenericObjectDefinitionAll(CFMENavigateStep):
    VIEW = GenericObjectDefinitionAllView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Automation', 'Automate', 'Generic Objects')


@navigator.register(GenericObjectDefinitionCollection, 'Add')
class GenericObjectDefinitionAdd(CFMENavigateStep):
    VIEW = GenericObjectDefinitionAddView

    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Generic Object Class')


@navigator.register(GenericObjectDefinition, 'Details')
class GenericObjectDefinitionDetails(CFMENavigateStep):
    VIEW = GenericObjectDefinitionDetailsView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(GenericObjectDefinition, 'Edit')
class GenericObjectDefinitionEdit(CFMENavigateStep):
    VIEW = GenericObjectDefinitionEditView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Generic Object Class')



