import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic.xpath import quote
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.automate.dialogs import AddBoxView
from cfme.automate.dialogs import AutomateCustomizationView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import parent_of_type
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from widgetastic_manageiq import DialogBootstrapSwitch
from widgetastic_manageiq import DialogButton
from widgetastic_manageiq import DialogElement
from widgetastic_manageiq import DragandDrop
from widgetastic_manageiq import EntryPoint
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import WaitTab


class ElementForm(AddBoxView):
    title = Text('//div[@id= "main-content"]//h1')
    ele_save_button = DialogButton('Save')
    ele_cancel_button = DialogButton('Cancel')
    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @View.nested
    class element_information(WaitTab):  # noqa
        TAB_NAME = 'Field Information'
        element_tree = ManageIQTree('dialog_edit_treebox')
        dynamic_tree = ManageIQTree('automate_treebox')
        bt_tree = ManageIQTree('automate_treebox')

        ele_label = Input(name='label')
        ele_name = Input(name="name")
        ele_desc = Input(name="description")
        dynamic_chkbox = BootstrapSwitch(label='Dynamic')

    @View.nested
    class options(WaitTab):  # noqa
        default_text_box = Input(name='default_value')
        entry_point = EntryPoint(
            locator="//input[@class='form-control']",
            tree_id="treeview-tree-selector"
        )
        field_required = DialogBootstrapSwitch(label='Required')
        default_value = DialogBootstrapSwitch(label='Default value')
        default_value_dropdown = BootstrapSelect(
            locator='//label[contains(normalize-space(.), '
                    '"Default value")]/following-sibling::div/span/div'
        )
        field_past_dates = DialogBootstrapSwitch(label='Show Past Dates')
        field_category = Select(
            locator='.//select[../../../../label[normalize-space(text())="Category"]]')
        multi_select = DialogBootstrapSwitch(label='Multiselect')
        validation_switch = DialogBootstrapSwitch(label='Validation')
        validation = Input(name='validator_rule')
        visible = DialogBootstrapSwitch(label='Visible')

    @View.nested
    class advanced(WaitTab):  # noqa
        reconfigurable = BootstrapSwitch(label='Reconfigurable')


class DialogsView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'All Dialogs' and
            self.service_dialogs.is_opened and
            self.service_dialogs.tree.currently_selected == ["All Dialogs"])


class AddElementView(ElementForm):

    component = Text(locator='.//div[normalize-space(.)="Drag your components here"]')
    add_section = Text(locator='.//div/i[normalize-space(.)="fa-plus-circle"]')
    element = DialogElement()
    edit_icon = DialogElement()

    def before_fill(self, values):
        element_type = values.get('element_information').get('choose_type')
        self.element.edit_element(element_type)

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.title.text == "Automate Customization" and
            self.component.is_displayed or not self.add_section.is_displayed
        )


class EditElementView(ElementForm):
    element = DialogElement()
    label = Input(id='name')
    dragndrop = DragandDrop()

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.title.text == "Automate Customization" and
            self.label.read() == self.context['object'].dialog.label
        )


class DetailsDialogView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == 'Dialog "{}"'.format(self.context['object'].dialog.label)
        )


@attr.s
class Element(BaseEntity):
    """A class representing one Element of a dialog."""
    element_data = attr.ib()

    @property
    def tree_path(self):
        return self.parent.tree_path

    @property
    def dialog(self):
        """ Returns parent object - Dialog"""
        from cfme.automate.dialogs.service_dialogs import Dialog
        return parent_of_type(self, Dialog)

    def element_loc(self, element_type):
        return self.browser.element('.//dialog-editor-field/div[@class="form-group"]'
                                    '/label[normalize-space(.)={}]'.format(quote(element_type)))

    def add_another_element(self, element):
        """Method to add element."""
        view = navigate_to(self, 'Edit')
        dragged_element = element.get('element_information').get('choose_type')
        box_label = element.get('element_information').get('ele_label')
        view.dd.drag_and_drop(dragged_element, box_label)
        view.element.edit_element(dragged_element)
        view.fill(element)
        view.ele_save_button.click()
        view.save_button.click()
        view = self.create_view(DetailsDialogView, wait='10s')
        view.flash.assert_no_error()

    def reorder_elements(self, add_element, second_element, element_data):
        """Method to add element and interchange element positions.
           This method updates a dialog and adds a second element.The position
           of two elements are then interchanged to test for error.(BZ-1238721)

        Args:
            add_element: flag if second element needs to be added.
            second_element: The second element to be added to the dialog.
            element_data: Already existing first element's data.
        """
        view = navigate_to(self, 'Edit')
        if add_element:
            dragged_element = second_element.get('element_information').get('choose_type')
            box_label = second_element.get('element_information').get('ele_label')
            view.cancel_button.click()
            view.dd.drag_and_drop(dragged_element, box_label)
            view.element.edit_element(dragged_element)
            view.fill(second_element)
            view.ele_save_button.click()
        dragged_el = element_data.get('element_information').get("ele_label")
        dropped_el = second_element.get('element_information').get("ele_label")
        view.dragndrop.drag_and_drop(self.element_loc(dragged_el), self.element_loc(dropped_el))
        view.save_button.click()
        view = self.create_view(DetailsDialogView, wait='10s')
        view.flash.assert_no_error()


@attr.s
class ElementCollection(BaseCollection):

    ENTITY = Element

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, element_data):
        for element in element_data:
            view = navigate_to(self, "Add")
            dragged_element = element.get('element_information').get('choose_type')
            view.dd.drag_and_drop(dragged_element, self.parent.box_label)
            view.fill(element)
            view.ele_save_button.click()
        if view.save_button.disabled:
            logger.warning('Save button disabled during Dialog Element creation')
            return False
        else:
            view.save_button.click()
        view.flash.wait_displayed(timeout=5)
        view.flash.assert_no_error()
        return self.instantiate(element_data=element_data)

    def set_element_type(self, view, element):
        """ Method to add element type.Depending on their type the subfields varies.

        Args:
            each_element: subfields depending on element type.
        """
        choose_type = element.get("choose_type")
        dynamic_chkbox = element.get("dynamic_chkbox")
        element_type = ['Dropdown', 'Radio Button']
        if choose_type in element_type:
            if not dynamic_chkbox:
                row = view.entry_table.row(Value='<New Entry>')
                row.click()
                view.fill({'entry_value': "Yes",
                           'entry_description': "entry_desc"})
                view.add_entry_button.click()
            else:
                node1 = "InspectMe"
                view.fill({'field_entry_point': 'b'})
                view.bt_tree.click_path("Datastore", "new_domain", "System", "Request", node1)
                view.apply_btn.click()
                view.fill({'field_show_refresh_button': True})
        if choose_type == "Text Area Box":
            view.fill({'text_area': 'Default text'})


@navigator.register(ElementCollection)
class Add(CFMENavigateStep):
    VIEW = AddElementView

    prerequisite = NavigateToAttribute('parent.parent', 'Add')

    def step(self, *args, **kwargs):
        self.prerequisite_view.dd.drag_and_drop("Text Box", self.obj.parent.box_label)


@navigator.register(Element, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = EditElementView

    prerequisite = NavigateToAttribute('dialog', 'Edit')

    def step(self, *args, **kwargs):
        self.prerequisite_view.element.edit_element(
            self.obj.element_data[0]['element_information']['ele_label']
        )
