from widgetastic.utils import Parameter
from widgetastic.widget import Text
from widgetastic_manageiq import MultiBoxSelect
from widgetastic_patternfly import Button, Input
from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import WidgetasticTaggable
from cfme.utils.update import Updateable
from cfme.utils.pretty import Pretty
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils import version

from . import ServicesCatalogView


class CatalogsMultiBoxSelect(MultiBoxSelect):
    move_into_button = Button(title=Parameter("@move_into"))
    move_from_button = Button(title=Parameter("@move_from"))


class CatalogForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    name = Input(name='name')
    description = Input(name="description")
    assign_catalog_items = CatalogsMultiBoxSelect(
        move_into="Move Selected buttons right",
        move_from="Move Selected buttons left",
        available_items="available_fields",
        chosen_items="selected_fields"
    )

    save_button = Button('Save')
    cancel_button = Button('Cancel')


class CatalogsView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'All Catalogs' and
            self.catalogs.is_opened and
            self.catalogs.tree.currently_selected == ["All Catalogs"])


class DetailsCatalogView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.catalogs.is_opened and
            self.title.text == 'Catalog "{}"'.format(self.context['object'].name)
        )


class AddCatalogView(CatalogForm):

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.catalogs.is_opened and
            self.title.text == "Adding a new Catalog"
        )


class EditCatalogView(CatalogForm):

    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and self.catalogs.is_opened and
            self.title.text == "Editing Catalog {}".format(self.name)
        )


class Catalog(Updateable, Pretty, Navigatable, WidgetasticTaggable):

    def __init__(self, name=None, description=None, items=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.items = items

    def create(self):
        view = navigate_to(self, 'Add')
        view.fill({
            'name': self.name,
            'description': self.description,
            'assign_catalog_items': self.items
        })
        view.add_button.click()
        view.flash.assert_success_message('Catalog "{}" was saved'.format(self.name))
        view = self.create_view(CatalogsView)
        assert view.is_displayed
        view.flash.assert_no_error()

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(DetailsCatalogView, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Catalog "{}" was saved'.format(updates.get('name', self.name)))
        else:
            view.flash.assert_message(
                'Edit of Catalog "{}" was cancelled by the user'.format(self.name))

    def delete(self):
        view = navigate_to(self, "Details")
        view.configuration.item_select(
            version.pick({
                version.LOWEST: 'Remove Item from the VMDB',
                '5.7': 'Remove Catalog'}),
            handle_alert=True)
        view = self.create_view(CatalogsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_success_message(
            'Catalog "{}": Delete successful'.format(self.description or self.name))

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        # web_ui.Table.click_row_by_cells throws a NameError exception on no match
        except NameError:
            return False


@navigator.register(Catalog, 'All')
class All(CFMENavigateStep):
    VIEW = CatalogsView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.catalogs.tree.click_path("All Catalogs")


@navigator.register(Catalog, 'Add')
class Add(CFMENavigateStep):
    VIEW = AddCatalogView

    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a New Catalog')


@navigator.register(Catalog, 'Details')
class Details(CFMENavigateStep):
    VIEW = DetailsCatalogView

    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.catalogs.tree.click_path("All Catalogs", self.obj.name)


@navigator.register(Catalog, 'Edit')
class Edit(CFMENavigateStep):
    VIEW = EditCatalogView

    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Item')
