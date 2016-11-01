from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.exceptions import ImageNotFound, BlockTypeUnknown
from cfme.common.vm import VM, Template
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, toolbar as tb, CheckboxTable, InfoBlock, match_location, \
    PagedTable
from cfme.web_ui.search import search_box
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to, CFMENavigateStep, navigator
from utils.log import logger
from . import cfg_btn, life_btn, pol_btn

list_table = PagedTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='vm_cloud', title='Instances')


def details_page_check(name, provider):
    title_match = match_page(summary='Image "{}"'.format(name))
    if title_match:
        # Also check provider
        # Limits scope of testing to images that aren't orphaned or archived, but if we don't do
        # this and multiple providers are present we might have multiple images with the same name
        try:
            prov_match = InfoBlock.text('Relationships', 'Cloud Provider') == provider
            return title_match and prov_match
        except BlockTypeUnknown:
            # Default to false since we can't identify which provider the image belongs to
            return False


@VM.register_for_provider_type("cloud")
class Image(Template, Navigatable):
    ALL_LIST_LOCATION = "clouds_images"
    TO_OPEN_EDIT = "Edit this Image"
    QUADICON_TYPE = "image"

    def __init__(self, name, provider, template_name=None, appliance=None):
        super(Image, self).__init__(name=name, provider=provider, template_name=template_name)
        Navigatable.__init__(self, appliance=appliance)

    def on_details(self, force=False):
        """A function to determine if the browser is already on the proper image details page.

            An image may not be assigned to a provider if archived or orphaned
            If no provider is listed, default to False since we may be on the details page
            for an image on the wrong provider.
        """
        if details_page_check(self.name, self.provider):
            return True
        elif not force:
            return False
        elif force:
            navigate_to(self, 'Details')
            return True


@navigator.register(Image, 'All')
class ImageAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary="All Images")

    def step(self, *args, **kwargs):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Instances')(None)

        # use accordion
        # If a filter was applied, it will persist through navigation and needs to be cleared
        if sel.is_displayed(search_box.clear_advanced_search):
            logger.debug('Clearing advanced search filter')
            sel.click(search_box.clear_advanced_search)
        accordion.tree('Images', 'All Images')


@navigator.register(Image, 'Details')
class ImageDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return details_page_check(name=self.obj.name, provider=self.obj.provider)

    def step(self):
        # Use list view to match name and provider
        tb.select('List View')
        cell = {'Name': self.obj.name, 'Provider': self.obj.provider.name}
        try:
            sel.click(list_table.find_row_by_cell_on_all_pages(cell))
        except NoSuchElementException:
            raise ImageNotFound('Could not find image matching {}'.format(cell))


@navigator.register(Image, 'ProvisionImage')
class ImageProvisionImage(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    # No am_i_here, page identifiers are not unique

    def step(self, *args, **kwargs):
        life_btn('Provision Instances using this Image')


@navigator.register(Image, 'EditSelected')
class ImageEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        cfg_btn('Edit this Image')


@navigator.register(Image, 'EditSelected')
class ImageEditSelected(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        check_table = CheckboxTable(table_locator="//div[@id='list_grid']//table")
        check_table.select_row_by_cells({'Name': self.obj.name,
                                         'Provider': self.obj.provider.name})
        cfg_btn('Edit selected Image')


@navigator.register(Image, 'SetOwnership')
class ImageSetOwnership(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        cfg_btn('Set Ownership')


@navigator.register(Image, 'ManagePolicies')
class ImageManagePolicies(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Manage Policies')


@navigator.register(Image, 'PolicySimulation')
class ImagePolicySimulation(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Policy Simulation')


@navigator.register(Image, 'EditTags')
class ImageEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Edit Tags')
