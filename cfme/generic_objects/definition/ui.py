from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import Text, View, ParametrizedString, ParametrizedLocator, Table
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, BaseEntitiesView, FileInput, ParametrizedSummaryTable,
    BootstrapSwitch, FonticonPicker, ManageIQTree, SummaryForm
)
from widgetastic_patternfly import (
    Input, BootstrapSelect, Dropdown, Button, CandidateNotFound, Accordion
)

from cfme.base.login import BaseLoggedInPage
from cfme.generic_objects.instance.ui import GenericObjectInstanceAllView
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to, ViaUI
from . import GenericObjectDefinition, GenericObjectDefinitionCollection


class GenericObjectDefinitionToolbar(View):
    configuration = Dropdown(text='Configuration')
    download = Dropdown(text='Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class GenericObjectDefinitionView(BaseLoggedInPage):

    @property
    def in_generic_object_definition(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Automation', 'Automate']
        )


class AccordionForm(View):

    @View.nested
    class classes(Accordion):   # noqa
        ACCORDION_NAME = "Generic Object Classes"
        tree = ManageIQTree()


class GenericObjectDefinitionAllView(GenericObjectDefinitionView):
    toolbar = View.nested(GenericObjectDefinitionToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)
    accordion = View.nested(AccordionForm)

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition and
            self.toolbar.configuration.is_displayed and
            self.entities.title.text == 'All Generic Object Classes'
        )


class ParametersForm(View):
    ROOT = ParametrizedLocator('//generic-object-table-component[@key-type="{@param_type}"]')
    ALL_PARAMETERS = './/input[contains(@class, "ng-not-empty")]'
    add = Button(ParametrizedString('Add {@param_type}'))
    name = Input(locator='.//input[contains(@class, "ng-empty")]')
    type_class = BootstrapSelect(
        locator='.//input[contains(@class, "ng-empty")]//ancestor::tr//button')

    def __init__(self, parent, param_type, logger=None):
        View.__init__(self, parent, logger=logger)
        self.param_type = param_type

    def all(self):
        return [(element.get_attribute('value'), element.get_attribute('name'))
                for element in self.browser.elements(self.ALL_PARAMETERS)]

    @property
    def empty_field_is_present(self):
        return self.browser.element(self.name).is_displayed()

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


class ButtonParameterForm(ParametersForm):
    type_class = Input(locator='.//input[contains(@class, "ng-empty") and contains(@id, "Value")]')
    add = Button('Add Attribute/Value Pair')


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

        def after_fill(self, was_change):
            if was_change:
                self.custom_image_file.upload_chosen_file.click()


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
    accordion = View.nested(AccordionForm)

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition and
            self.title.text == 'Generic Object Class {}'.format(self.context['object'].name)
        )


class GenericObjectAddButtonView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')

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
    attributes = ButtonParameterForm(param_type="Attribute")

    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.title.text == 'Add a new Custom Button' and self.in_generic_object_definition


class GenericObjectButtonGroupAddView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    display = BootstrapSwitch(name='display')
    description = Input(name='description')
    image = VersionPick({
        Version.lowest(): BootstrapSelect('button_image'),
        '5.9': FonticonPicker('button_icon')})

    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.title.text == 'GenericObjectButtonGroupAddView' and
            self.in_generic_object_definition
        )

    def after_fillafter_fill(self, was_change):
        # we need to click somewhere out side the form to get add button active,
        # after icon is filled
        if was_change:
            self.browser.element('//body').click()


class GenericObjectButtonGroupDetailsView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')
    configuration = Dropdown(text='Configuration')
    basic_information = SummaryForm('Basic Information')
    accordion = View.nested(AccordionForm)
    table = Table('//h3[contains(text(), "Buttons")]/following-sibling::table')

    @property
    def is_displayed(self):
        return (
            self.basic_information.is_displayed and
            self.in_generic_object_definition and
            'Custom Button Set' in self.title.text
        )


@MiqImplementationContext.external_for(GenericObjectDefinitionCollection.create, ViaUI)
def create(self, name, description, attributes=None, associations=None, methods=None,
           custom_image_file_path=None, cancel=False):
    """
    Create new generic object definition
    Args:
        name: generic object definition name
        description: generic object definition description
        attributes:  generic object definition attributes ex. {'address': 'string'}
        associations:  generic object definition associations ex. {'services': 'Service'}
        methods: generic object definition methods ex. ['method1', 'method2']
        custom_image_file_path: generic object definition custom image file path
        cancel: by default will not be canceled, pass True to make successful cancel

    Returns:
        GenericObjectDefinition entity

    """
    view = navigate_to(self, 'Add')
    view.fill({
        'name': name,
        'description': description,
        'associations': associations,
        'attributes': attributes,
        'methods': methods,
        'custom_image_file': {'file': custom_image_file_path}
    })
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
    """Update generic object definition

    Args:
        updates: dict, with fields to update
    """
    view = navigate_to(self, 'Edit')
    view.fill({
        'name': updates.get('name'),
        'description': updates.get('description'),
        'associations': updates.get('associations'),
        'attributes': updates.get('attributes'),
        'methods': updates.get('methods'),
        'custom_image_file': {'file': updates.get('custom_image_file_path')}
    })
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
    """Delete generic object definition
    """
    view = navigate_to(self, 'Details')

    view.configuration.item_select(
        'Remove this Generic Object Classes from Inventory', handle_alert=True)
    view = self.create_view(GenericObjectDefinitionAllView)
    assert view.is_displayed
    view.flash.assert_no_error()


@MiqImplementationContext.external_for(GenericObjectDefinition.add_button, ViaUI)
def add_button(self, name, description, image, request, button_type='Default', display=True,
               dialog=None, open_url=None, display_for=None, submit_version=None,
               system_message=None, attributes=None, role=None, button_group=None, cancel=False):
    """Add button to generic object definition
    """
    if button_group:
        view = navigate_to(self, 'AddButton', button_group=button_group)
    else:
        view = navigate_to(self, 'AddButton')
    view.fill({
        'button_type': button_type,
        'name': name,
        'description': description,
        'display': display,
        'image': image,
        'dialog': dialog,
        'open_url': open_url,
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
    view.flash.assert_no_error()


@MiqImplementationContext.external_for(GenericObjectDefinition.add_button_group, ViaUI)
def add_button_group(self, name, description, image, display=True, cancel=False):
    """Add button group for generic object definition
    """
    view = navigate_to(self, 'AddButtonGroup')
    view.fill({
        'image': image,
        'name': name,
        'description': description,
        'display': display,
    })
    if cancel:
        view.cancel.click()
    else:
        view.add.click()
    view = self.create_view(GenericObjectDefinitionDetailsView)
    assert view.is_displayed
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


@navigator.register(GenericObjectDefinitionCollection)
class All(CFMENavigateStep):
    VIEW = GenericObjectDefinitionAllView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Automation', 'Automate', 'Generic Objects')


@navigator.register(GenericObjectDefinitionCollection)
class Add(CFMENavigateStep):
    VIEW = GenericObjectDefinitionAddView

    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Generic Object Class')


@navigator.register(GenericObjectDefinition)
class Details(CFMENavigateStep):
    VIEW = GenericObjectDefinitionDetailsView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(GenericObjectDefinition)
class Edit(CFMENavigateStep):
    VIEW = GenericObjectDefinitionEditView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Generic Object Class')


@navigator.register(GenericObjectDefinition)
class Instances(CFMENavigateStep):
    VIEW = GenericObjectInstanceAllView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.summary('Relationships').click_at('Instances')


@navigator.register(GenericObjectDefinition)
class AddButtonGroup(CFMENavigateStep):
    VIEW = GenericObjectButtonGroupAddView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a new Button Group')


@navigator.register(GenericObjectDefinition)
class ButtonGroupDetails(CFMENavigateStep):
    VIEW = GenericObjectButtonGroupDetailsView

    prerequisite = NavigateToSibling('Details')

    def step(self, **kwargs):
        if kwargs:
            self.prerequisite_view.accordion.classes.tree.click_path(
                'All Generic Object Classes', self.obj.name, 'Actions',
                '{} (Group)'.format(kwargs.get('button_group')))


@navigator.register(GenericObjectDefinition)
class AddButton(CFMENavigateStep):
    VIEW = GenericObjectAddButtonView

    def prerequisite(self, **kwargs):
        if kwargs:
            return navigate_to(self.obj, 'ButtonGroupDetails', **kwargs)
        else:
            return navigate_to(self.obj, 'Details')

    def step(self, **kwargs):
        self.prerequisite(**kwargs).configuration.item_select('Add a new Button')
