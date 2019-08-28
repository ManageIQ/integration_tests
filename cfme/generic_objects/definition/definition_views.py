from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import ParametrizedString
from widgetastic.widget import ParametrizedLocator
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BootstrapSwitch
from widgetastic_manageiq import FileInput
from widgetastic_manageiq import FonticonPicker
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import Table


class GenericObjectDefinitionToolbar(View):
    configuration = Dropdown(text='Configuration')
    download = Dropdown(text='Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class GenericObjectDefinitionView(BaseLoggedInPage):
    @property
    def in_generic_object_definition(self):
        expected_nav = (
            ["Automation", "Automate"]
            if self.browser.appliance.version < "5.10"
            else ["Automation", "Automate", "Generic Objects"]
        )

        return (
            self.logged_in_as_current_user and self.navigation.currently_selected == expected_nav
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
    ROOT = ParametrizedLocator(
        "//generic-object-table-component[@key-type='{@param_type}'] "
        " | //generic-object-table[@key-type='{@param_type}']"
    )
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
        try:
            return self.browser.element(self.name)
        except NoSuchElementException:
            return False

    def add_parameter_row(self):
        if not self.empty_field_is_present:
            self.add.click()

    def fill(self, parameters):
        if parameters:
            if isinstance(parameters, dict):
                for name, type_class in parameters.items():
                    self.add_parameter_row()
                    type_result = self.type_class.fill(type_class.capitalize())
                    result = self.name.fill(name)
                    return result and type_result
            elif isinstance(parameters, list):
                for name in parameters:
                    self.add_parameter_row()
                    result = self.name.fill(name)
                    return result

    def delete(self, name):
        all_params = self.all()
        for param in all_params:
            param_name, element_name = param
            if param_name == name:
                self.browser.element(
                    '//td[contains(@ng-class,  "{}")]/ancestor::tr'
                    '//div[@title = "Delete Row"]'.format(element_name)).click()


class GenericObjectDefinitionAddEditView(GenericObjectDefinitionView):
    title = Text('//div[@id="main-content"]//div/h1')
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
            self.in_generic_object_definition
            and self.title.text
            == "Add a new Generic Object {}".format(
                "Definition" if self.browser.appliance.version >= "5.11" else "Class"
            )
        )


class GenericObjectDefinitionEditView(GenericObjectDefinitionAddEditView):

    save = Button('Save')
    reset = Button('Reset')

    @property
    def is_displayed(self):
        if self.browser.appliance.version >= "5.11":
            expected_title = "Edit a Generic Object Definition '{}'".format(
                self.context["object"].name
            )
        else:
            expected_title = "Edit Generic Object Class"

        return self.in_generic_object_definition and self.title.text == expected_title


class GenericObjectDefinitionDetailsView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')
    configuration = Dropdown(text='Configuration')
    summary = ParametrizedSummaryTable()
    accordion = View.nested(AccordionForm)

    @property
    def is_displayed(self):
        return (
            self.in_generic_object_definition and
            self.title.text == 'Generic Object Class {}'.format(
                self.context['object'].name)
        )


class ButtonParameterForm(ParametersForm):
    type_class = Input(locator='.//input[contains(@class, "ng-empty") and contains(@id, "Value")]')
    add = Button('Add Attribute/Value Pair')


class GenericObjectAddEditButtonView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')

    button_type = BootstrapSelect(name='button_type')
    name = Input(name='name')
    description = Input(name='description')
    display = BootstrapSwitch(name='display')
    image = FonticonPicker('button_icon')
    dialog = BootstrapSelect(name='dialog')
    open_url = BootstrapSwitch(name='open_url')
    display_for = BootstrapSelect(name='display_for')
    submit_version = BootstrapSelect(name='submit_how')
    system_process = BootstrapSelect(name='ae_instance')
    system_message = Input(name='ae_message')
    request = Input(name='request')
    add_attribute_value_key = Button('Add Attribute/Value Pair')
    attributes = ButtonParameterForm(param_type="Attribute")
    cancel = Button('Cancel')


class GenericObjectAddButtonView(GenericObjectAddEditButtonView):

    add = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Add a new Custom Button' and
            self.in_generic_object_definition and
            self.button_type.is_displayed
        )


class GenericObjectEditButtonView(GenericObjectAddEditButtonView):

    save = Button('Save')
    reset = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.title.text == f"Edit Custom Button '{self.context['object'].name}'" and
            self.in_generic_object_definition and
            self.button_type.is_displayed
        )


class GenericObjectActionsDetailsView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')
    group_table = Table('//h3[contains(text(), "Groups")]/following-sibling::table[1]')
    button_table = Table('//h3[contains(text(), "Buttons")]/following-sibling::table[1]')
    accordion = View.nested(AccordionForm)

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Actions for Generic Object Class' and
            self.in_generic_object_definition
        )


class GenericObjectButtonGroupAddView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    display = BootstrapSwitch(name='display')
    description = Input(name='description')
    image = FonticonPicker('button_icon')

    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.title.text == "Add a new Custom Button Group" and
            self.name.is_displayed and
            self.in_generic_object_definition
        )

    def after_fill(self, was_change):
        # we need to click somewhere out side the form to get add button active,
        # after icon is filled
        if was_change:
            self.browser.element('//body').click()


class GenericObjectButtonGroupEditView(GenericObjectButtonGroupAddView):
    save = Button('Save')
    reset = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.title.text == f"Edit Custom Button Group '{self.context['object'].name}'" and
            self.in_generic_object_definition
        )


class GenericObjectButtonDetailsView(GenericObjectDefinitionView):
    title = Text('#explorer_title_text')
    configuration = Dropdown(text='Configuration')
    basic_information = SummaryForm('Basic Information')
    accordion = View.nested(AccordionForm)

    @property
    def is_displayed(self):
        return (
            self.basic_information.is_displayed and
            self.in_generic_object_definition and
            self.title.text == f"Custom Button {self.context['object'].name}"
        )


class GenericObjectButtonGroupDetailsView(GenericObjectButtonDetailsView):
    button_table = Table('//h3[contains(text(), "Buttons")]/following-sibling::table')

    @property
    def is_displayed(self):
        return (
            self.basic_information.is_displayed and
            self.in_generic_object_definition and
            'Custom Button Set' in self.title.text
        )
