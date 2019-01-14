import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, View
from widgetastic_patternfly import Button, BootstrapSelect

from cfme.modeling.base import BaseCollection
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from . import (AllCatalogItemView, BasicInfoForm, DetailsCatalogItemView, NonCloudInfraCatalogItem,
    ServicesCatalogView)
from cfme.utils.version import LOWEST, VersionPicker
from widgetastic_manageiq import WaitTab


class CatalogBundleFormView(ServicesCatalogView):
    title = Text('#explorer_title_text')

    @View.nested
    class basic_info(WaitTab):  # noqa
        TAB_NAME = 'Basic Info'
        included_form = View.include(BasicInfoForm)

    @View.nested
    class resources(WaitTab):  # noqa
        select_resource = BootstrapSelect('resource_id')


class AddCatalogBundleView(CatalogBundleFormView):
    cancel_button = Button('Cancel')
    apply_button = Button('Apply')
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Adding a new Catalog Bundle'
        )


class EditCatalogBundleView(CatalogBundleFormView):
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Editing Catalog Bundle "{}"'.format(self.context["object"].name)
        )


@attr.s
class CatalogBundle(NonCloudInfraCatalogItem):

    catalog_items = attr.ib(default=None)

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.resources.fill({'select_resource': updates.get('catalog_items')})
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        if changed:
            view.flash.assert_success_message(
                'Catalog Bundle "{}" was saved'.format(updates.get('name', self.name)))
        else:
            view.flash.assert_success_message(
                'Edit of Catalog Bundle"{}" was cancelled by the user'.format(self.name))
        view = self.create_view(DetailsCatalogItemView, override=updates, wait='10s')
        view.flash.assert_no_error()


class CatalogBundlesCollection(BaseCollection):
    ENTITY = CatalogBundle

    def create(self, name, catalog_items=None, catalog=None, description=None, display_in=None,
               dialog=None, domain="ManageIQ (Locked)"):
        # TODO Move this logic into the view, the main obstacle is filling 'catalog_items'
        view = navigate_to(self, 'Add')

        # In 5.10 catalog name is appended with 'My Company'
        cat_name = VersionPicker({
            LOWEST: getattr(catalog, 'name', None),
            '5.10': 'My Company/{}'.format(getattr(catalog, 'name', None))
        }).pick(self.appliance.version)

        view.basic_info.fill({
            'name': name,
            'description': description,
            'display': display_in,
            'select_catalog': cat_name,
            'select_dialog': dialog
        })
        if view.basic_info.field_entry_point.value == "":
            view.basic_info.fill({'field_entry_point': ''})
            view.basic_info.tree.click_path(
                "Datastore", domain, "Service", "Provisioning",
                "StateMachines", "ServiceProvision_Template", "CatalogItemInitialization")
            view.apply_button.click()
        for cat_item in catalog_items:
            view.resources.fill({'select_resource': cat_item})
        view.add_button.click()
        view.flash.assert_success_message('Catalog Bundle "{}" was added'.format(name))
        view = self.create_view(AllCatalogItemView, wait='10s')
        view.flash.assert_no_error()
        return self.instantiate(name, catalog_items=catalog_items, catalog=catalog,
                                description=description, display_in=display_in, dialog=dialog,
                                domain=domain)


@navigator.register(CatalogBundlesCollection, 'All')
class All(CFMENavigateStep):
    VIEW = AllCatalogItemView
    prerequisite = NavigateToAttribute('appliance.server', 'ServicesCatalog')

    def step(self):
        self.view.catalog_items.tree.click_path('All Catalog Items')


@navigator.register(CatalogBundlesCollection, 'Add')
class BundleAdd(CFMENavigateStep):
    VIEW = AddCatalogBundleView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select('Add a New Catalog Bundle')


@navigator.register(CatalogBundle, 'Edit')
class BundleEdit(CFMENavigateStep):
    VIEW = EditCatalogBundleView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select('Edit this Item')
