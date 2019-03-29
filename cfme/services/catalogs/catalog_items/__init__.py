import re

import attr
import fauxfactory
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Checkbox
from widgetastic.widget import ClickableMixin
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
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
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from cfme.utils.wait import wait_for
from widgetastic_manageiq import FonticonPicker
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import WaitTab


class EntryPoint(Input, ClickableMixin):
    def fill(self, value):
        if super(EntryPoint, self).fill(value):
            self.parent_view.modal.cancel.wait_displayed('20s')
            self.parent_view.modal.cancel.click()
            # After changing default path values of 'retirement_entry_point',
            # 'reconfigure_entry_point' or 'provisioning_entry_point';
            # 'Select Entry Point Instance'(pop up) occures which also helps to select these paths
            # using tree structure. Here we have already filled these values through text input.
            # So to ignore this pop up clicking on cancel button is required.
            return True
        return False


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
    provisioning_entry_point = EntryPoint(name='fqname')
    retirement_entry_point = EntryPoint(name='retire_fqname')
    reconfigure_entry_point = EntryPoint(name='reconfigure_fqname')
    select_resource = BootstrapSelect('resource_id')

    @View.nested
    class modal(View):  # noqa
        tree = ManageIQTree('automate_treebox')
        include_domain = Checkbox(id='include_domain_prefix_chk')
        apply = Button('Apply')
        cancel = Button('Cancel')


class ButtonGroupForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    btn_group_text = Input(name='name')
    btn_group_hvr_text = Input(name='description')
    btn_image = FonticonPicker('button_icon')


class ButtonForm(ServicesCatalogView):
    title = Text('#explorer_title_text')

    btn_text = Input(name='name')
    btn_hvr_text = Input(name='description')
    btn_image = BootstrapSelect('button_image')
    select_dialog = BootstrapSelect('dialog_id')
    system_process = BootstrapSelect('instance_name')
    request = Input(name='object_request')

    @View.nested
    class options(WaitTab):    # noqa
        TAB_NAME = 'Options'

        btn_text = Input(name='name')
        btn_hvr_text = Input(name='description')
        select_dialog = BootstrapSelect('dialog_id')
        btn_image = FonticonPicker('button_icon')

    @View.nested
    class advanced(WaitTab):   # noqa
        TAB_NAME = 'Advanced'

        system_process = BootstrapSelect('instance_name')
        request = Input(name='object_request')


class AllCatalogItemView(ServicesCatalogView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'All Service Catalog Items' and
            self.catalog_items.is_opened and
            self.catalog_items.tree.currently_selected == ['All Catalog Items']
        )


class DetailsCatalogItemView(ServicesCatalogView):
    title = Text('#explorer_title_text')

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.catalog_items.is_opened and
            self.title.text == 'Service Catalog Item "{}"'.format(self.context['object'].name)
        )


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

    @property
    def button_icon_name(self):
        return 'broom'

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
        view.configuration.item_select('Remove Catalog Item', handle_alert=True)
        view = self.create_view(AllCatalogItemView)
        assert view.is_displayed
        view.flash.assert_success_message('The selected Catalog Item was deleted')

    def add_button_group(self, **kwargs):
        button_name = kwargs.get("text", "gp_{}".format(fauxfactory.gen_alpha()))
        hover_name = kwargs.get("hover", "hover_{}".format(fauxfactory.gen_alpha()))
        image = kwargs.get("image", "broom")

        view = navigate_to(self, "AddButtonGroup")
        view.fill(
            {
                "btn_group_text": button_name,
                "btn_group_hvr_text": hover_name,
                "btn_image": image,
            }
        )
        view.add.click()
        view = self.create_view(DetailsCatalogItemView, wait="10s")
        view.flash.assert_no_error()
        return button_name

    def button_group_exists(self, name):
        view = navigate_to(self, "Details")
        path = view.catalog_items.tree.read()
        path.extend(["Actions", "{} (Group)".format(name)])

        try:
            view.catalog_items.tree.fill(path)
            return True
        except CandidateNotFound:
            return False

    def delete_button_group(self, name):
        view = navigate_to(self, "Details")
        path = view.catalog_items.tree.read()
        path.extend(["Actions", "{} (Group)".format(name)])
        view.catalog_items.tree.fill(path)
        view.configuration.item_select("Remove this Button Group", handle_alert=True)
        view.flash.assert_no_error()

        # TODO(BZ-1687289): To avoid improper page landing adding a workaround.
        if BZ(1687289).blocks:
            view.browser.refresh()

    def add_button(self):
        button_name = fauxfactory.gen_alpha()
        view = navigate_to(self, 'AddButton')
        if self.appliance.version < '5.9':
            view.fill({'btn_text': 'btn_text',
                'btn_hvr_text': button_name,
                'btn_image': self.button_icon_name,
                'select_dialog': self.dialog,
                'system_process': 'Request',
                'request': 'InspectMe'})
        else:
            view.fill({'options': {'btn_text': 'btn_text',
                                   'btn_hvr_text': button_name,
                                   'select_dialog': self.dialog,
                                   'btn_image': self.button_icon_name},
                       'advanced': {'system_process': 'Request',
                                    'request': 'InspectMe'}})
        view.add.click()
        view = self.create_view(DetailsCatalogItemView)
        wait_for(lambda: view.is_displayed, timeout=5)
        view.flash.assert_no_error()
        return button_name

    @property
    def catalog_name(self):
        # In 5.10 catalog name is appended with 'My Company'
        cat_name = VersionPicker({
            LOWEST: getattr(self.catalog, 'name', None),
            '5.10': 'My Company/{}'.format(getattr(self.catalog, 'name', None))
        }).pick(self.appliance.version)
        return cat_name


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
    provisioning_entry_point = attr.ib(default=(
        "/Service/Provisioning/StateMachines/ServiceProvision_Template/CatalogItemInitialization"))
    retirement_entry_point = attr.ib(
        default="/Service/Retirement/StateMachines/ServiceRetirement/Default"
    )
    reconfigure_entry_point = attr.ib(default='')

    @property
    def fill_dict(self):
        return {
            'basic_info': {
                'name': self.name,
                'description': self.description,
                'display': self.display_in,
                'select_catalog': self.catalog_name,
                'select_dialog': self.dialog,
                'provisioning_entry_point': self.provisioning_entry_point,
                'retirement_entry_point': self.retirement_entry_point,
                'reconfigure_entry_point': self.reconfigure_entry_point
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

    @cached_property
    def _fill_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'display': self.display_in,
            'select_catalog': self.catalog_name,
            'select_dialog': self.dialog
        }


class AmazonCatalogItem(CloudInfraCatalogItem):
    item_type = 'Amazon'


@attr.s
class AnsibleTowerCatalogItem(NonCloudInfraCatalogItem):
    provider = attr.ib(default=None)
    config_template = attr.ib(default=None)

    @property
    def item_type(self):
        if self.appliance.version >= '5.9':
            return 'Ansible Tower'
        else:
            return 'AnsibleTower'

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
    @property
    def item_type(self):
        if self.appliance.version >= '5.9.0.17':
            return 'Red Hat Virtualization'
        else:
            return 'RHEV'


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
        cat_item = self.instantiate(catalog_item_class, *args, **kwargs)
        view = navigate_to(cat_item, "Add")
        view.fill(cat_item.fill_dict)
        view.add.click()
        view = self.create_view(AllCatalogItemView, wait='10s')
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
