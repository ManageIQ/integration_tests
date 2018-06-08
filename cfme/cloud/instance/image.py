import attr
from navmazing import NavigateToAttribute, NavigateToSibling, NavigationDestinationNotFound
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View
from widgetastic_patternfly import Button, Dropdown

from cfme.common.vm import Template, TemplateCollection
from cfme.common.vm_views import (
    EditView, SetOwnershipView, PolicySimulationView, BasicProvisionFormView,
    VMDetailsEntities, VMEntities)
from cfme.exceptions import ImageNotFound, DestinationNotFound
from cfme.utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from cfme.utils.providers import get_crud_by_name
from widgetastic_manageiq import ItemsToolBarViewSelector, SummaryTable, ItemNotFound
from . import CloudInstanceView, InstanceAccordion


class ImageToolbar(View):
    """
    Toolbar view for image collection
    """
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    configuration = Dropdown('Configuration')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ImageDetailsToolbar(View):
    """
        Toolbar view for image collection
        """
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    configuration = Dropdown('Configuration')
    lifecycle = Dropdown('Lifecycle')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class ImageDetailsEntities(VMDetailsEntities):
    pass


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


@attr.s
class Image(Template):
    ALL_LIST_LOCATION = "clouds_images"
    TO_OPEN_EDIT = "Edit this Image"
    QUADICON_TYPE = "image"

    @property
    def exists(self):
        """Whether the image exists in CFME"""
        try:
            navigate_to(self, 'Details')
        except ImageNotFound:
            return False
        return True


@attr.s
class ImageCollection(TemplateCollection):
    ENTITY = Image

    def all(self):
        """Return entities for all items in image collection"""
        # Pretty much same as instance, but defining at VMCollection would only work for cloud
        # provider filter means we're viewing images through provider details relationships
        provider = self.filters.get('provider')  # None if no filter, need for entity instantiation
        view = navigate_to(self,
                           'AllForProvider' if provider else 'All')
        # iterate pages here instead of use surf_pages=True because data is needed
        entities = []
        for _ in view.entities.paginator.pages():  # auto-resets to first page
            page_entities = [entity for entity in view.entities.get_all(surf_pages=False)]
            entities.extend(
                # when provider filtered view, there's no provider data value
                [self.instantiate(e.data['name'], provider or get_crud_by_name(e.data['provider']))
                 for e in page_entities
                 if e.data.get('provider') != '']  # safe provider check, archived shows no provider
            )
        return entities


@navigator.register(ImageCollection, 'All')
@navigator.register(Image, 'All')
class ImageAll(CFMENavigateStep):
    VIEW = ImageAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Instances')
        self.view.sidebar.images.tree.click_path('All Images')


@navigator.register(ImageCollection, 'AllForProvider')
@navigator.register(Image, 'AllForProvider')
class ImageAllForProvider(CFMENavigateStep):
    VIEW = ImageProviderAllView

    def prerequisite(self):
        try:
            view = navigate_to(self.obj, 'All')
        except NavigationDestinationNotFound:
            view = navigate_to(self.obj.parent, 'All')
        finally:
            return view

    def step(self, *args, **kwargs):
        """Navigate to provider filtered collection
        Raises:
            CollectionFilterngError: When the collection has not yet been filtered
        """
        if isinstance(self.obj, ImageCollection) and self.obj.filters.get('provider'):
            # the collection is navigation target, use its filter value
            provider_name = self.obj.filters['provider'].name
        elif isinstance(self.obj, Image):
            # entity is navigation target, use its provider attr
            provider_name = self.obj.provider.name
        else:
            raise DestinationNotFound("Unable to identify a provider for AllForProvider navigation")

        self.view.sidebar.images_by_provider.tree.click_path('Images by Provider', provider_name)

    def resetter(self):
        self.view.entities.search.remove_search_filters()


@navigator.register(Image, 'Details')
class ImageDetails(CFMENavigateStep):
    VIEW = ImageDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True)
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


@navigator.register(Image, 'PolicySimulation')
class ImagePolicySimulation(CFMENavigateStep):
    VIEW = PolicySimulationView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Policy Simulation')
