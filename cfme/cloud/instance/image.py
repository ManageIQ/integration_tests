from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View, Text
from widgetastic_patternfly import Button, Dropdown, FlashMessages
from widgetastic_manageiq import ItemsToolBarViewSelector, SummaryTable, ItemNotFound

from cfme.exceptions import ImageNotFound
from cfme.common.vm import Template
from cfme.common.vm_views import (
    EditView, SetOwnershipView, ManagePoliciesView, PolicySimulationView, BasicProvisionFormView,
    VMEntities)
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from . import CloudInstanceView, InstanceAccordion


class ImageToolbar(View):
    """
    Toolbar view for image collection
    """
    reload = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ImageDetailsToolbar(View):
    """
        Toolbar view for image collection
        """
    reload = Button(title='Reload current display')
    configuration = Dropdown('Configuration')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class ImageDetailsEntities(View):
    title = Text('//div[@id="main-content"]//h1//span[@id="explorer_title_text"]')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')
    properties = SummaryTable(title='Properties')
    lifecycle = SummaryTable(title='Lifecycle')
    relationships = SummaryTable(title='Relationships')
    compliance = SummaryTable(title='Compliance')
    power_management = SummaryTable(title='Power Management')
    security = SummaryTable(title='Security')
    configuration = SummaryTable(title='Configuration')
    smart_management = SummaryTable(title='Smart Management')


class ImageAllView(CloudInstanceView):
    """View for the Image collection"""
    toolbar = View.nested(ImageToolbar)
    sidebar = View.nested(InstanceAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            self.sidebar.images.is_opened and
            self.sidebar.images.tree.selected_item.text == 'All Images' and
            self.entities.title.text == 'All Images')


class ImageProviderAllView(CloudInstanceView):
    """View for the Image collection"""
    toolbar = View.nested(ImageToolbar)
    sidebar = View.nested(InstanceAccordion)
    including_entities = View.include(VMEntities, use_parent=True)

    @property
    def is_displayed(self):
        expected_title = 'Images under Provider "{}"'.format(self.context['object'].provider.name)
        accordion = self.sidebar.images_by_provider
        return (
            self.in_cloud_instance and
            accordion.is_opened and
            accordion.tree.selected_item.text == self.context['object'].provider.name and
            self.entities.title.text == expected_title)


class ImageDetailsView(CloudInstanceView):
    """View for an Image"""
    toolbar = View.nested(ImageToolbar)
    sidebar = View.nested(InstanceAccordion)
    entities = View.nested(ImageDetailsEntities)
    tag = SummaryTable(title='Smart Management')  # to satisfy WidgetasticTagable, CHANGEME

    @property
    def is_displayed(self):
        accordion = self.sidebar.images_by_provider
        relationships = self.entities.relationships
        return (
            self.in_cloud_instance and
            accordion.is_opened and
            accordion.tree.selected_item.text == self.context['object'].provider.name and
            relationships.get_text_of('Cloud Provider') == self.context['object'].provider.name and
            self.entities.title.text == 'Image "{}"'.format(self.context['object'].name))


class ImageProvisionView(CloudInstanceView):
    """
    View for provisioning image, built from common provisioning form.
    No before_fill, image already selected
    """
    @View.nested
    class form(BasicProvisionFormView):  # noqa
        """Tabs from BasicProvisionFormView, just adding buttons
        """
        submit = Button('Submit')  # Submit for 2nd page, tabular form
        cancel = Button('Cancel')

    @property
    def is_displayed(self):
        prov_name = self.context['object'].provider.name
        return (
            self.in_cloud_instance and
            self.form.is_displayed and
            self.form.catalog.catalog_name.currently_selected == self.context['object'].name and
            len(self.form.catalog.catalog_name.read_content()) == 1 and
            self.form.catalog.catalog_name.read_content()[0].get('Provider', None) == prov_name)


class Image(Template, Navigatable):
    ALL_LIST_LOCATION = "clouds_images"
    TO_OPEN_EDIT = "Edit this Image"
    QUADICON_TYPE = "image"

    def __init__(self, name, provider, template_name=None, appliance=None):
        super(Image, self).__init__(name=name, provider=provider, template_name=template_name)
        Navigatable.__init__(self, appliance=appliance)

    @property
    def exists(self):
        """Whether the image exists in CFME"""
        try:
            navigate_to(self, 'Details')
        except ImageNotFound:
            return False
        return True


@navigator.register(Image, 'All')
class ImageAll(CFMENavigateStep):
    VIEW = ImageAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Instances')
        self.view.sidebar.images.tree.click_path('All Images')


@navigator.register(Image, 'AllForProvider')
class ImageAllForProvider(CFMENavigateStep):
    VIEW = ImageProviderAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Instances')
        self.view.sidebar.images_by_provider.tree.click_path('Images by Provider',
                                                             self.obj.provider.name)


@navigator.register(Image, 'Details')
class ImageDetails(CFMENavigateStep):
    VIEW = ImageDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise ImageNotFound('Failed to locate image with name "{}"'.format(self.obj.name))
        row.click()


@navigator.register(Image, 'ProvisionImage')
class ImageProvisionImage(CFMENavigateStep):
    VIEW = ImageProvisionView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select('Provision Instances using this Image')


@navigator.register(Image, 'Edit')
class ImageEdit(CFMENavigateStep):
    VIEW = EditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Image')


@navigator.register(Image, 'SetOwnership')
class ImageSetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(Image, 'ManagePolicies')
class ImageManagePolicies(CFMENavigateStep):
    VIEW = ManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(Image, 'PolicySimulation')
class ImagePolicySimulation(CFMENavigateStep):
    VIEW = PolicySimulationView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Policy Simulation')
