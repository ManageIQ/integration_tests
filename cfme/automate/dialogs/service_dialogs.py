import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import Fillable
from widgetastic.widget import Text

from cfme.automate.dialogs import AddDialogView
from cfme.automate.dialogs import AutomateCustomizationView
from cfme.automate.dialogs import CopyDialogView
from cfme.automate.dialogs import EditDialogView
from cfme.automate.dialogs.dialog_tab import TabCollection
from cfme.exceptions import RestLookupError
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Table


class DialogsView(AutomateCustomizationView):
    title = Text("#explorer_title_text")
    paginator = PaginationPane()
    table = Table(".//div[@id='list_grid' or @class='miq-data-table']/table")

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
    """A class representing one Dialog in the UI."""
    label = attr.ib()
    description = attr.ib(default=None)

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
        view.flash.wait_displayed(timeout=20)
        assert view.is_displayed
        view.flash.assert_no_error()

    def delete(self):
        """ Delete dialog method"""
        view = navigate_to(self, "Details")
        view.configuration.item_select('Remove Dialog', handle_alert=True)
        view = self.create_view(DialogsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_success_message(
            'Dialog "{}": Delete successful'.format(self.label))

    def copy(self):
        view = navigate_to(self, "Copy")
        view.save_button.click()
        view = self.create_view(DetailsDialogView)
        view.flash.assert_success_message(f'Copy of {self.label} was saved')
        view.flash.wait_displayed(timeout=20)
        assert view.is_displayed
        view.flash.assert_no_error

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.service_dialogs.get(label=self.label)
        except ValueError:
            raise RestLookupError(
                f"No service dialog rest entity found matching label {self.label}"
            )


@attr.s
class DialogCollection(BaseCollection):
    """Collection object for the :py:class:`Dialog`."""

    tree_path = ['All Dialogs']
    ENTITY = Dialog

    def create(self, label=None, description=None):
        """ Create dialog label method """
        view = navigate_to(self, 'Add')
        view.fill({'label': label, 'description': description})
        return self.instantiate(
            label=label, description=description)


@navigator.register(DialogCollection)
class All(CFMENavigateStep):
    VIEW = DialogsView

    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self, *args, **kwargs):
        self.view.service_dialogs.tree.click_path(*self.obj.tree_path)


@navigator.register(DialogCollection)
class Add(CFMENavigateStep):
    VIEW = AddDialogView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a new Dialog')


@navigator.register(Dialog)
class Details(CFMENavigateStep):
    VIEW = DetailsDialogView

    prerequisite = NavigateToAttribute('appliance.server', 'AutomateCustomization')

    def step(self, *args, **kwargs):
        self.prerequisite_view.service_dialogs.tree.click_path(*self.obj.tree_path)


@navigator.register(Dialog)
class Edit(CFMENavigateStep):
    VIEW = EditDialogView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Dialog")


@navigator.register(Dialog)
class Copy(CFMENavigateStep):
    VIEW = CopyDialogView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Copy this Dialog')
