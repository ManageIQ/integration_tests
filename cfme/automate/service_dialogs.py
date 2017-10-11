import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text
from widgetastic.utils import Fillable
from widgetastic_patternfly import CandidateNotFound
from cached_property import cached_property

from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

from . import AutomateCustomizationView, AddDialogView, EditDialogView
from .dialog_tab import TabCollection


class DialogsView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization and
            self.title.text == 'All Dialogs' and
            self.service_dialogs.is_opened and
            self.service_dialogs.tree.currently_selected == ["All Dialogs"])


class DetailsDialogView(AutomateCustomizationView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_customization and self.service_dialogs.is_opened and
            self.title.text == 'Dialog "{}"'.format(self.context['object'].label)
        )


@attr.s
class Dialog(BaseEntity, Fillable):
    """A class representing one Domain in the UI."""
    label = attr.ib()
    description = attr.ib(default=None)
    submit = attr.ib(default=False)
    cancel = attr.ib(default=False)

    _collections = {'tabs': TabCollection}

    def as_fill_value(self):
        return self.label

    @property
    def dialog(self):
        return self

    @cached_property
    def tabs(self):
        return self.collections.tabs

    @property
    def tree_path(self):
        return self.parent.tree_path + [self.label]

    def update(self, updates):
        """ Update dialog method"""
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(DetailsDialogView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Dialog "{}" was saved'.format(updates.get('name', self.label)))
        else:
            view.flash.assert_message(
                'Edit of Dialog "{}" was cancelled by the user'.format(self.label))

    def delete(self):
        """ Delete dialog method"""
        view = navigate_to(self, "Details")
        view.configuration.item_select('Remove Dialog', handle_alert=True)
        view = self.create_view(DialogsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_success_message(
            'Dialog "{}": Delete successful'.format(self.label))

    @property
    def exists(self):
        """ Returns True if dialog exists"""
        try:
            navigate_to(self, 'Details')
            return True
        except (CandidateNotFound, ItemNotFound):
            return False

    def delete_if_exists(self):
        if self.exists:
            self.delete()


@attr.s
class DialogCollection(BaseCollection):
    """Collection object for the :py:class:`Dialog`."""

    tree_path = ['All Dialogs']
    ENTITY = Dialog

    def create(self, label=None, description=None, submit=False, cancel=False):
        """ Create dialog label method """
        view = navigate_to(self, 'Add')
        # filling label twice to avoid the selenium field bug
        fill_dict = {
            k: v
            for k, v in {'label': label, 'description': description,
                         'submit_button': submit, 'cancel_button': cancel}.items()
            if v is not None}
        view.fill(fill_dict)
        view.fill({'label': label})
        return self.instantiate(
            label=label, description=description, submit=submit, cancel=cancel)


@navigator.register(DialogCollection)
class All(CFMENavigateStep):
    VIEW = DialogsView

    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
            self.view.service_dialogs.tree.click_path(*self.obj.tree_path)


@navigator.register(DialogCollection)
class Add(CFMENavigateStep):
    VIEW = AddDialogView

    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a new Dialog')


@navigator.register(Dialog)
class Details(CFMENavigateStep):
    VIEW = DetailsDialogView

    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self):
        self.prerequisite_view.service_dialogs.tree.click_path(*self.obj.tree_path)


@navigator.register(Dialog)
class Edit(CFMENavigateStep):
    VIEW = EditDialogView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Dialog")
