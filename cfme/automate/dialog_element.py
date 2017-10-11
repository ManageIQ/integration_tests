import attr

from navmazing import NavigateToAttribute
from widgetastic.widget import Checkbox, Image, Text
from widgetastic_patternfly import Button, Input, BootstrapSelect
from widgetastic_manageiq import ManageIQTree, Table, TextInput
from widgetastic.xpath import quote

from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

from . import AutomateCustomizationView, AddBoxView


class ElementForm(AddBoxView):
    ele_label = Input(name='field_label')
    ele_name = Input(name="field_name")
    ele_desc = Input(name="field_description")
    choose_type = BootstrapSelect('field_typ')
    default_text_box = Input(name='field_default_value')
    default_value = Checkbox(name='field_default_value')
    field_required = Checkbox(name='field_required')
    field_past_dates = Checkbox(name='field_past_dates')
    field_entry_point = Input(name='field_entry_point')
    field_show_refresh_button = Checkbox(name='field_show_refresh_button')
    entry_value = Input(name='entry[value]')
    entry_description = Input(name='entry[description]')
    add_entry_button = Image('.//input[@id="accept"]')
    field_category = BootstrapSelect('field_category')
    text_area = Input(name='field_default_value')
    dynamic_chkbox = Checkbox(name='field_dynamic')
    entry_table = Table('//div[@id="field_values_div"]/form/table')
    text_area = TextInput(id='field_default_value')

    element_tree = ManageIQTree('dialog_edit_treebox')
    dynamic_tree = ManageIQTree('automate_treebox')
    bt_tree = ManageIQTree('automate_treebox')

    apply_btn = Button('Apply')


class AddElementView(ElementForm):

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Adding a new Dialog [Element Information]"
        )


class EditElementView(ElementForm):
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Editing Dialog {} [Element Information]".format(self.ele_label)
        )


class DetailsDialogView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == 'Dialog "{}"'.format(self.context['object'].
                dialog.label)
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
        from .service_dialogs import Dialog
        return parent_of_type(self, Dialog)

    def element_loc(self, element_data):
        return self.browser.element('//div[@class="panel-heading"]'
            '[contains(normalize-space(.), {})]/..'.format(quote(element_data)))

    def add_another_element(self, element):
        """Method to add element."""
        view = navigate_to(self, 'Edit')
        view.element_tree.click_path(*self.tree_path[1:])
        view.plus_btn.item_select("Add a new Element to this Box")
        view.fill(element)
        view.save_button.click()
        view = self.create_view(DetailsDialogView)
        assert view.is_displayed
        view.flash.assert_no_error()

    def reorder_elements(self, add_element, second_element, element_data):
        """Method to add element and interchange element positions.
           This method updates a dialog and adds a second element.The position
           of two elements are then interchanged to test for error.

        Args:
            add_element - flag if second element needs to be added.
            second_element - The second element to be added to the dialog.
            element_data - Already existing first element's data.
        """
        view = navigate_to(self, 'Edit')
        view.element_tree.click_path(*self.tree_path[1:])
        # Add a new element and then interchange position (BZ-1238721)
        if add_element:
            view.plus_btn.item_select("Add a new Element to this Box")
            view.fill(second_element)
            view.element_tree.click_path(*self.tree_path[1:])
        self.browser.drag_and_drop(self.element_loc(element_data.get("ele_label")),
            self.element_loc(second_element.get("ele_label")))
        view.save_button.click()
        view = self.create_view(DetailsDialogView)
        assert view.is_displayed
        view.flash.assert_no_error()


@attr.s
class ElementCollection(BaseCollection):

    ENTITY = Element

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, element_data=None):
        for element in element_data:
            view = navigate_to(self, "Add")
            if(view.ele_label.value != ""):
                view.plus_btn.item_select("Add a new Element to this Box")
            view.fill(element)
            self.set_element_type(view, element)
        view.add_button.click()
        view.flash.assert_no_error()
        view.flash.assert_message('Dialog "{}" was added'.
            format(self.parent.tab.dialog.label))
        view.flash.assert_no_error()
        return self.instantiate(element_data=element_data)

    def set_element_type(self, view, element):
        """ Method to add element type.Depending on their type the subfields varies.

        Args:
            each_element: subfields depending on element type.
        """
        choose_type = element.get("choose_type")
        dynamic_chkbox = element.get("dynamic_chkbox")
        element_type = ['Drop Down List', 'Radio Button']
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

    def step(self):
        self.prerequisite_view.plus_btn.item_select("Add a new Element to this Box")


@navigator.register(Element, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = EditElementView

    prerequisite = NavigateToAttribute('dialog', 'Edit')
