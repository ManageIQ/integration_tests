import re

import attr
import fauxfactory
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Checkbox
from widgetastic.widget import ColourInput
from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
from widgetastic_patternfly import CheckableBootstrapTreeview
from widgetastic_patternfly import Input

from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.common.vm_views import BasicProvisionFormView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.services.catalogs import ServicesCatalogView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import AutomateRadioGroup
from widgetastic_manageiq import EntryPoint
from widgetastic_manageiq import FileInput
from widgetastic_manageiq import FonticonPicker
from widgetastic_manageiq import InputButton
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import ReactSelect
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table
from widgetastic_manageiq import WaitTab
from widgetastic_manageiq.expression_editor import ExpressionEditor


# Views
class BasicInfoForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    # Filling dropdowns first to avoid selenium field reset bug
    select_catalog = BootstrapSelect('catalog_id')
    select_dialog = BootstrapSelect('dialog_id')

    select_provider = BootstrapSelect('manager_id')
    select_orch_template = BootstrapSelect('template_id')
    select_config_template = BootstrapSelect('template_id')

    name = Input(name='name')
    description = Input(name='description')
    display = Checkbox(name='display')

    subtype = BootstrapSelect('generic_subtype')
    provisioning_entry_point = EntryPoint(name='fqname', tree_id="automate_catalog_treebox")
    retirement_entry_point = EntryPoint(name='retire_fqname', tree_id="automate_catalog_treebox")
    reconfigure_entry_point = EntryPoint(name='reconfigure_fqname',
        tree_id="automate_catalog_treebox")
    select_resource = BootstrapSelect('resource_id')
    additional_tenants = CheckableBootstrapTreeview(tree_id="tenants_treebox")
    zone = BootstrapSelect("zone_id")
    currency = BootstrapSelect("currency")
    price_per_month = Input(name="price")

    @View.nested
    class modal(View):  # noqa
        tree = ManageIQTree('automate_treebox')
        include_domain = Checkbox(id='include_domain_prefix_chk')
        apply = Button('Apply')
        cancel = Button('Cancel')


class ButtonGroupForm(ServicesCatalogView):
    title = Text("#explorer_title_text")

    text = Input(name="name")
    display = Checkbox(name="display")
    hover = Input(name="description")
    icon = FonticonPicker("button_icon")
    icon_color = ColourInput(id="button_color")


class ButtonForm(ServicesCatalogView):
    title = Text("#explorer_title_text")

    @View.nested
    class options(WaitTab):  # noqa
        btn_type = BootstrapSelect("button_type")
        form = ConditionalSwitchableView(reference="btn_type")

        @form.register("Default")
        class ButtonFormDefaultView(View):  # noqa
            dialog = BootstrapSelect("dialog_id")

        @form.register("Ansible Playbook")
        class ButtonFormAnsibleView(View):  # noqa
            playbook_cat_item = BootstrapSelect("service_template_id")
            inventory = AutomateRadioGroup(locator=".//input[@name='inventory']/..")
            hosts = Input(name="hosts")

        text = Input(name="name")
        display = Checkbox(name="display")
        hover = Input(name="description")
        icon = FonticonPicker("button_icon")
        icon_color = ColourInput(id="button_color")
        open_url = Checkbox("open_url")
        display_for = Select(id="display_for")
        submit = Select(id="submit_how")

    @View.nested
    class advanced(WaitTab):  # noqa
        @View.nested
        class enablement(View):  # noqa
            title = Text('//*[@id="ab_form"]/div[1]/h3')
            define_exp = Text(locator='//*[@id="form_enablement_expression_div"]//a/button')
            expression = ExpressionEditor()
            disabled_text = Input(id="disabled_text")

        @View.nested
        class visibility(View):  # noqa
            title = Text('//*[@id="ab_form"]/h3[2]')
            define_exp = Text(locator='//*[@id="form_visibility_expression_div"]//a/button')
            expression = ExpressionEditor()

        system = BootstrapSelect("instance_name")
        message = Input(name="object_message")
        request = Input(name="object_request")


class AllCatalogItemView(ServicesCatalogView):
    title = Text('#explorer_title_text')
    table = Table('//*[@id="miq-gtl-view"]/miq-data-table/div/table')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'All Service Catalog Items' and
            self.catalog_items.is_opened and
            self.catalog_items.tree.currently_selected == ['All Catalog Items']
        )


class DetailsEntitiesCatalogItemView(View):
    upload_image = FileInput(id="upload_image")
    upload_button = InputButton("commit")
    remove = Button(title="Remove this Custom Image")
    smart_management = SummaryTable("Smart Management")


class DetailsCatalogItemView(ServicesCatalogView):
    title = Text('#explorer_title_text')
    basic_info = SummaryForm("Basic Information")
    currency_price = Text(locator='.//div[../label[contains(text(), "Price / Month")]]')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Service Catalog Item "{}"'.format(self.context['object'].name)
        )

    entities = View.nested(DetailsEntitiesCatalogItemView)


class ChooseCatalogItemTypeView(ServicesCatalogView):
    """Intermediate view where an actual catalog item type is selected."""
    select_item_type = BootstrapSelect('st_prov_type', can_hide_on_select=True)
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Adding a new Service Catalog Item'
        )


class AddCatalogItemView(BasicInfoForm):
    """NonCloudInfraCatalogItem catalog items have this view."""
    fill_strategy = WaitFillViewStrategy()
    add = Button('Add')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Adding a new Service Catalog Item'
        )


class AddOrchestrationCatalogItemView(AddCatalogItemView):
    fill_strategy = WaitFillViewStrategy()

    @property
    def widget_names(self):
        # there are several derived views, widgets in those views are displayed in different order
        # this property is just workaround in order to change widget bypass order
        return ['title', 'select_catalog', 'select_dialog',
                'select_orch_template', 'select_config_template', 'select_provider',
                'name', 'description', 'display',
                'subtype', 'field_entry_point', 'retirement_entry_point', 'select_resource']


class TabbedAddCatalogItemView(ServicesCatalogView):
    """Cloud and Infra catalog items have this view."""
    add = Button('Add')
    cancel = Button('Cancel')

    @View.nested
    class basic_info(WaitTab):  # noqa
        TAB_NAME = 'Basic Info'
        included_form = View.include(BasicInfoForm)

    class request_info(WaitTab):  # noqa
        TAB_NAME = 'Request Info'
        provisioning = View.nested(BasicProvisionFormView)

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Adding a new Service Catalog Item'
        )


class EditCatalogItemView(BasicInfoForm):
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text
            == 'Editing Service Catalog Item "{}"'.format(self.context["object"].name)
        )

    def after_fill(self, was_change):
        # TODO: This is a workaround (Jira RHCFQE-5429)
        if was_change:
            wait_for(lambda: not self.save.disabled, timeout='10s', delay=0.2)


class CopyCatalogItemView(ServicesCatalogView):
    name = Input(name="name")

    add = Button("Add")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.title.text == f'Service Catalog Item "{self.context["object"].name}"'
            and self.catalog_items.is_opened
            and self.catalog_items.is_dimmed
        )


class TabbedEditCatalogItemView(ServicesCatalogView):
    fill_strategy = WaitFillViewStrategy()
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @View.nested
    class basic_info(WaitTab):  # noqa
        TAB_NAME = 'Basic Info'
        included_form = View.include(BasicInfoForm)

    class request_info(WaitTab):  # noqa
        TAB_NAME = 'Request Info'
        provisioning = View.nested(BasicProvisionFormView)

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text
            == 'Editing Service Catalog Item "{}"'.format(self.context['object'].name)
        )


class ButtonGroupDetailView(ServicesCatalogView):
    title = Text("#explorer_title_text")

    text = SummaryFormItem(
        "Basic Information",
        "Text",
        text_filter=lambda text: re.sub(r"\s+Display on Button\s*$", "", text),
    )
    hover = SummaryFormItem("Basic Information", "Hover Text")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            "Button Group" in self.title.text
        )


class AddButtonGroupView(ButtonGroupForm):

    add = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Adding a new Button Group'
        )


class AddButtonView(ButtonForm):

    add = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Adding a new Button'
        )


class BaseCatalogItem(BaseEntity, Updateable, Pretty, Taggable):

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        changed = view.fill(updates)
        if changed:
            view.save.click()
        else:
            view.cancel.click()
        view = self.create_view(DetailsCatalogItemView, override=updates, wait='10s')
        view.flash.assert_no_error()

    def delete(self):
        view = navigate_to(self, 'Details')
        view.configuration.item_select('Delete Catalog Item', handle_alert=True)

        view = self.create_view(AllCatalogItemView, wait="20s")
        assert view.is_displayed
        view.flash.assert_success_message(f'The catalog item "{self.name}"'
            ' has been successfully deleted')

    def copy(self, name=None):
        view = navigate_to(self, 'Copy')

        # there is default name like `Copy of *`
        if name:
            view.name.fill(name)

        copied_name = view.name.value
        view.add.click()
        view.flash.assert_no_error()

        # Catalog item can be any type
        item_args = self.__dict__
        item_args["name"] = copied_name
        return self.__class__(**item_args)

    def add_button_group(self, **kwargs):
        button_name = kwargs.get("text", fauxfactory.gen_alpha(start="grp_"))
        hover_name = kwargs.get("hover", fauxfactory.gen_alpha(15, start="grp_hvr_"))

        view = navigate_to(self, "AddButtonGroup")
        view.fill(
            {
                "text": button_name,
                "display": kwargs.get("display", True),
                "hover": hover_name,
                "icon": kwargs.get("image", "broom"),
                "icon_color": kwargs.get("icon_color")
            }
        )
        view.add.click()
        view = self.create_view(DetailsCatalogItemView, wait="10s")
        view.flash.assert_no_error()
        return button_name

    def button_group_exists(self, name):
        view = navigate_to(self, "Details")
        path = view.catalog_items.tree.read()

        path.extend(["Actions", f"{name} (Group)"])

        try:
            view.catalog_items.tree.fill(path)
            return True
        except CandidateNotFound:
            return False

    def delete_button_group(self, name):
        view = navigate_to(self, "Details")
        path = view.catalog_items.tree.read()

        path.extend(["Actions", f"{name} (Group)"])
        view.catalog_items.tree.fill(path)
        view.configuration.item_select("Remove this Button Group", handle_alert=True)
        view.flash.assert_no_error()

        # TODO(BZ-1687289): To avoid improper page landing adding a workaround.
        if BZ(1687289, forced_streams=['5.11']).blocks:
            view.browser.refresh()

    def add_button(self, **kwargs):
        text = kwargs.get("text", fauxfactory.gen_alpha(start="btn_"))
        hover = kwargs.get("hover", fauxfactory.gen_alpha(15, start="btn_hvr_"))

        view = navigate_to(self, "AddButton")
        view.fill(
            {
                "options": {
                    "btn_type": kwargs.get("type"),
                    "dialog": kwargs.get("dialog"),
                    "playbook_cat_item": kwargs.get("playbook_cat_item"),
                    "inventory": kwargs.get("inventor"),
                    "hosts": kwargs.get("hosts"),
                    "text": text,
                    "display": kwargs.get("display", True),
                    "hover": hover,
                    "icon": kwargs.get("image", "broom"),
                    "icon_color": kwargs.get("icon_color"),
                    "open_url": kwargs.get("open_url"),
                    "display_for": kwargs.get("display_for"),
                    "submit": kwargs.get("submit"),
                },
                "advanced": {
                    "system": kwargs.get("system", "Request"),
                    "request": kwargs.get("request", "InspectMe"),
                },
            }
        )
        view.add.click()
        view = self.create_view(DetailsCatalogItemView, wait=5)
        view.flash.assert_no_error()
        return text

    def button_exists(self, name):
        view = navigate_to(self, "Details")
        path = view.catalog_items.tree.read()
        path.extend(["Actions", name])

        try:
            view.catalog_items.tree.fill(path)
            return True
        except CandidateNotFound:
            return False

    def delete_button(self, name):
        view = navigate_to(self, "Details")
        path = view.catalog_items.tree.read()
        path.extend(["Actions", name])
        view.catalog_items.tree.fill(path)
        view.configuration.item_select("Remove this Button", handle_alert=True)
        view.flash.assert_no_error()

        # TODO(BZ-1687289): To avoid improper page landing adding a workaround.
        if BZ(1687289, forced_streams=['5.11']).blocks:
            view.browser.refresh()

    @property
    def catalog_name(self):
        cat_name = 'My Company/{}'.format(getattr(self.catalog, 'name', None))
        return cat_name

    @staticmethod
    def set_additional_tenants(view, tenants):
        """ Sets additional tenants

        Args:
            view: AddCatalogItemView or EditCatalogItemView
            tenants: list of tenants with options to select

        Usage:
            set True to the path which needs to be checked
            and False for the path that needs to be unchecked

        catalog_item = appliance.collections.catalog_items.create(
            catalog_item_class,
            additional_tenants=[
                (("All Tenants"), False),
                (("All Tenants", "My Company"), True),
                (("All Tenants", "My Company", "Child", "Grandchild"), True),
            ],
            *args,
            **kwargs
        )
        """
        if tenants is not None and isinstance(tenants, (list, tuple, set)):
            changes = [
                view.fill(
                    {
                        "additional_tenants": CheckableBootstrapTreeview.CheckNode(path)
                        if option
                        else CheckableBootstrapTreeview.UncheckNode(path)
                    }
                )
                for path, option in tenants
            ]
            return True in changes
        else:
            return False

    def set_ownership(self, owner, group):
        view = navigate_to(self, "SetOwnership")
        view.form.select_an_owner.fill(owner)
        view.form.select_group.fill(group)
        view.submit.click()


class SetOwnershipView(ServicesCatalogView):
    submit = Button("Submit")
    reset = Button("Reset")
    cancel = Button("Cancel")

    @View.nested
    class form(View):
        select_an_owner = ReactSelect("user_name")
        select_group = ReactSelect("group_name")

    @property
    def is_displayed(self):
        return (
            self.form.select_an_owner.is_displayed
            and self.form.select_group.is_displayed
            and self.submit.is_displayed
            and self.cancel.is_enabled
        )


@attr.s
class CloudInfraCatalogItem(BaseCatalogItem):
    """Catalog items that relate to cloud and infra providers."""
    name = attr.ib()
    prov_data = attr.ib()
    catalog = attr.ib(default=None)
    description = attr.ib(default=None)
    display_in = attr.ib(default=None)
    dialog = attr.ib(default=None)
    domain = attr.ib(default='ManageIQ (Locked)')
    provider = attr.ib(default=None)
    item_type = None
    provisioning_entry_point = attr.ib(default=None)
    retirement_entry_point = attr.ib(default=None)
    reconfigure_entry_point = attr.ib(default=None)
    zone = attr.ib(default=None)
    currency = attr.ib(default=None)
    price_per_month = attr.ib(default=None)
    additional_tenants = attr.ib(default=None)

    @property
    def fill_dict(self):
        return {
            'basic_info': {
                'name': self.name,
                'description': self.description,
                'display': self.display_in,
                'select_catalog': self.catalog_name if self.catalog else "<Unassigned>",
                'select_dialog': self.dialog,
                'provisioning_entry_point': self.provisioning_entry_point,
                'retirement_entry_point': self.retirement_entry_point,
                'reconfigure_entry_point': self.reconfigure_entry_point,
                "additional_tenants": self.additional_tenants,
                "zone": self.zone,
                "currency": self.currency,
                "price_per_month": self.price_per_month
            },
            'request_info': {'provisioning': self.prov_data}
        }


@attr.s
class NonCloudInfraCatalogItem(BaseCatalogItem):
    """Generic, Ansible Tower, Orchestration and OpenShift catalog items."""
    name = attr.ib()
    catalog = attr.ib(default=None)
    description = attr.ib(default=None)
    display_in = attr.ib(default=None)
    dialog = attr.ib(default=None)
    domain = attr.ib(default='ManageIQ (Locked)')
    provider = attr.ib(default=None)
    item_type = None
    provisioning_entry_point = attr.ib(default=None)
    retirement_entry_point = attr.ib(default=None)
    reconfigure_entry_point = attr.ib(default=None)
    zone = attr.ib(default=None)
    currency = attr.ib(default=None)
    price_per_month = attr.ib(default=None)
    additional_tenants = attr.ib(default=None)

    @cached_property
    def _fill_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'display': self.display_in,
            'select_catalog': self.catalog_name if self.catalog else "<Unassigned>",
            'select_dialog': self.dialog,
            'provisioning_entry_point': self.provisioning_entry_point,
            'retirement_entry_point': self.retirement_entry_point,
            'reconfigure_entry_point': self.reconfigure_entry_point,
            "additional_tenants": self.additional_tenants,
            "zone": self.zone,
            "currency": self.currency,
            "price_per_month": self.price_per_month
        }


class AmazonCatalogItem(CloudInfraCatalogItem):
    item_type = 'Amazon'


@attr.s
class AnsibleTowerCatalogItem(NonCloudInfraCatalogItem):
    item_type = 'Ansible Tower'

    provider = attr.ib(default=None)
    config_template = attr.ib(default=None)

    @property
    def fill_dict(self):
        self._fill_dict['select_provider'] = self.provider
        self._fill_dict['select_config_template'] = self.config_template
        return self._fill_dict


class AzureCatalogItem(CloudInfraCatalogItem):
    item_type = 'Azure'


@attr.s
class GenericCatalogItem(NonCloudInfraCatalogItem):
    subtype = attr.ib(default=None)
    item_type = 'Generic'

    @property
    def fill_dict(self):
        self._fill_dict['subtype'] = self.subtype
        return self._fill_dict


class GoogleCatalogItem(CloudInfraCatalogItem):
    item_type = 'Google'


@attr.s
class OpenShiftCatalogItem(NonCloudInfraCatalogItem):
    provider = attr.ib(default=None)
    item_type = 'OpenShift Template'

    @property
    def fill_dict(self):
        self._fill_dict['select_provider'] = self.provider
        return self._fill_dict


class OpenStackCatalogItem(CloudInfraCatalogItem):
    item_type = 'OpenStack'


@attr.s
class OrchestrationCatalogItem(NonCloudInfraCatalogItem):
    orch_template = attr.ib(default=None)
    item_type = 'Orchestration'
    provider_name = attr.ib(default=None)

    @property
    def fill_dict(self):
        self._fill_dict['select_config_template'] = getattr(
            self.orch_template, 'template_name', None)
        self._fill_dict['select_provider'] = self.provider_name
        return self._fill_dict


class RHVCatalogItem(CloudInfraCatalogItem):
    item_type = 'Red Hat Virtualization'


class SCVMMCatalogItem(CloudInfraCatalogItem):
    item_type = 'SCVMM'


class VMwareCatalogItem(CloudInfraCatalogItem):
    item_type = 'VMware'


@attr.s
class CatalogItemsCollection(BaseCollection):
    ENTITY = BaseCatalogItem
    AMAZON = AmazonCatalogItem
    ANSIBLE_TOWER = AnsibleTowerCatalogItem
    AZURE = AzureCatalogItem
    GENERIC = GenericCatalogItem
    GOOGLE = GoogleCatalogItem
    OPENSHIFT = OpenShiftCatalogItem
    OPENSTACK = OpenStackCatalogItem
    ORCHESTRATION = OrchestrationCatalogItem
    RHV = RHVCatalogItem
    SCVMM = SCVMMCatalogItem
    VMWARE = VMwareCatalogItem

    # damn circular imports
    @property
    def ANSIBLE_PLAYBOOK(self):  # noqa
        from cfme.services.catalogs.catalog_items import ansible_catalog_items
        return ansible_catalog_items.AnsiblePlaybookCatalogItem

    def instantiate(self, catalog_item_class, *args, **kwargs):
        return catalog_item_class.from_collection(self, *args, **kwargs)

    def create(self, catalog_item_class, *args, **kwargs):
        """Creates a catalog item in the UI.

        Args:
            catalog_item_class: type of a catalog item
            *args: see the respectful catalog item class
            **kwargs: see the respectful catalog item class

        Returns:
            An instance of catalog_item_class
        """
        additional_tenants = kwargs.pop("additional_tenants", None)

        cat_item = self.instantiate(catalog_item_class, * args, **kwargs)
        view = navigate_to(cat_item, "Add")
        if additional_tenants:
            cat_item.set_additional_tenants(view, additional_tenants)
        view.fill(cat_item.fill_dict)
        cat_item.additional_tenants = additional_tenants
        view.add.click()
        view = self.create_view(AllCatalogItemView, wait="10s")
        view.flash.assert_no_error()
        return cat_item


# Navigation steps
@navigator.register(CatalogItemsCollection, 'All')
class All(CFMENavigateStep):
    VIEW = AllCatalogItemView
    prerequisite = NavigateToAttribute('appliance.server', 'ServicesCatalog')

    def step(self, *args, **kwargs):
        self.view.catalog_items.tree.click_path('All Catalog Items')


@navigator.register(CatalogItemsCollection, 'Choose Type')
class ChooseCatalogItemType(CFMENavigateStep):
    VIEW = ChooseCatalogItemTypeView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a New Catalog Item')


@navigator.register(BaseCatalogItem, 'Add')
class CatalogItemAddStep(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Choose Type')

    @property
    def VIEW(self):  # noqa
        if isinstance(self.obj, CloudInfraCatalogItem):
            return TabbedAddCatalogItemView
        elif isinstance(self.obj, OrchestrationCatalogItem):
            # Orchestration View has different order of widgets than the rest
            return AddOrchestrationCatalogItemView
        else:
            return AddCatalogItemView

    def step(self, *args, **kwargs):
        self.prerequisite_view.select_item_type.select_by_visible_text(self.obj.item_type)


@navigator.register(BaseCatalogItem, 'Details')
class CatalogItemDetailsStep(CFMENavigateStep):
    VIEW = DetailsCatalogItemView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        tree = self.prerequisite_view.catalog_items.tree
        tree.click_path(
            'All Catalog Items',
            getattr(self.obj.catalog, 'name', 'Unassigned'),
            self.obj.name
        )


@navigator.register(BaseCatalogItem, 'Edit')
class CatalogItemEditStep(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    @property
    def VIEW(self):  # noqa
        if isinstance(self.obj, CloudInfraCatalogItem):
            return TabbedEditCatalogItemView
        else:
            return EditCatalogItemView

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Edit this Item')


@navigator.register(BaseCatalogItem, "Copy")
class CatalogItemCopyStep(CFMENavigateStep):
    VIEW = CopyCatalogItemView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Copy Selected Item")


@navigator.register(BaseCatalogItem, 'AddButtonGroup')
class AddButtonGroup(CFMENavigateStep):
    VIEW = AddButtonGroupView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a new Button Group')


@navigator.register(BaseCatalogItem, 'AddButton')
class AddButton(CFMENavigateStep):
    VIEW = AddButtonView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select('Add a new Button')


@navigator.register(BaseCatalogItem, 'EditTagsFromDetails')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.policy.item_select('Edit Tags')


@navigator.register(BaseCatalogItem, "SetOwnership")
class CatalogItemSetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Set Ownership")
