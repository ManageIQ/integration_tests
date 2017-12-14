import attr

from navmazing import NavigateToAttribute
from cached_property import cached_property

from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

from . import AddBoxView, BoxForm
from .dialog_element import ElementCollection


class EditBoxView(BoxForm):
    """EditBox View."""
    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == "Editing Dialog {} [Box Information]".format(self.box_label)
        )


@attr.s
class Box(BaseEntity):
    """A class representing one Box of dialog."""
    box_label = attr.ib()
    box_desc = attr.ib(default=None)

    _collections = {'elements': ElementCollection}

    @cached_property
    def elements(self):
        return self.collections.elements

    @property
    def tree_path(self):
        return self.parent.tree_path + [self.box_label]

    @property
    def tab(self):
        from .dialog_tab import Tab
        return parent_of_type(self, Tab)


@attr.s
class BoxCollection(BaseCollection):

    ENTITY = Box

    @property
    def tree_path(self):
        return self.parent.tree_path

    def create(self, box_label=None, box_desc=None):
        """Create box method.
           Args:
             box_label and box_description.
        """
        view = navigate_to(self, "Add")
        view.new_box.click()
        view.edit_box.click()
        view.fill({'box_label': box_label, 'box_desc': box_desc})
        view.save_button.click()
        return self.instantiate(box_label=box_label, box_desc=box_desc)


@navigator.register(BoxCollection)
class Add(CFMENavigateStep):
    VIEW = AddBoxView

    prerequisite = NavigateToAttribute('parent.parent', 'Add')

    def step(self):
        self.prerequisite_view.add_section.click()
