import attr

from widgetastic.utils import Parameter
from widgetastic.widget import Text
from widgetastic_manageiq import MultiBoxSelect
from widgetastic_patternfly import Button, Input
from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import Taggable
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.update import Updateable
from cfme.utils.pretty import Pretty
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to

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
            self.title.text == 'Editing Catalog "{}"'.format(self.context["object"].name)
        )


@attr.s
class Catalog(BaseEntity, Updateable, Pretty, Taggable):

    name = attr.ib()
    description = attr.ib()
    items = attr.ib(default=None)

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
        view.configuration.item_select('Remove Catalog', handle_alert=True)
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
        except NameError:
            return False


@attr.s
class CatalogCollection(BaseCollection):
    """A collection for the :py:class:`cfme.services.catalogs.catalog.Catalog`"""
    ENTITY = Catalog

    def create(self, name, description, items=None):
        """Create a catalog.

        Args:
            name: The name of the catalog
            description: The description of the catalog
            items: Items in the catalog
        """
        view = navigate_to(self, 'Add')
        view.fill({
            'name': name,
            'description': description,
            'assign_catalog_items': items
        })
        view.add_button.click()
        catalog = self.instantiate(name=name, description=description, items=items)
        view = self.create_view(CatalogsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        return catalog


@navigator.register(CatalogCollection)
class All(CFMENavigateStep):
    VIEW = CatalogsView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Services', 'Catalogs')
        self.view.catalogs.tree.click_path("All Catalogs")


@navigator.register(CatalogCollection)
class Add(CFMENavigateStep):
    VIEW = AddCatalogView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a New Catalog')


@navigator.register(Catalog)
class Details(CFMENavigateStep):
    VIEW = DetailsCatalogView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.catalogs.tree.click_path("All Catalogs", self.obj.name)


@navigator.register(Catalog)
class Edit(CFMENavigateStep):
    VIEW = EditCatalogView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Item')
