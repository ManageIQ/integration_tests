import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import NoSuchElementException
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class ObjectStoreContainerToolbar(View):
    """The toolbar on the Object Store Containers page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ObjectStoreContainerDetailsToolbar(View):
    """The toolbar on the Object Store Containers detail page"""
    policy = Dropdown('Policy')
    download = Button(title='Print or export summary')


class ObjectStoreContainerDetailsEntities(View):
    """The entities on the Object Store Containers detail page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class ObjectStoreContainerDetailSidebar(View):
    """The accordion on the Object Store Containers details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class ObjectStoreContainerView(BaseLoggedInPage):
    """A base view for all the Object Store Containers pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_container(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Storage', 'Object Storage',
                                                   'Object Store Containers'])


class ObjectStoreContainerAllView(ObjectStoreContainerView):
    """The all Object Store Containers page"""
    toolbar = View.nested(ObjectStoreContainerToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_container and
            self.title.text == 'Cloud Object Store Containers')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class ObjectStoreContainerDetailsView(ObjectStoreContainerView):
    """The detail Object Store containers page"""
    @property
    def is_displayed(self):
        obj = self.context['object']

        return (
            self.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb
        )

    toolbar = View.nested(ObjectStoreContainerDetailsToolbar)
    sidebar = View.nested(ObjectStoreContainerDetailSidebar)
    entities = View.nested(ObjectStoreContainerDetailsEntities)


@attr.s
class ObjectStoreContainer(BaseEntity, CustomButtonEventsMixin, Taggable):
    """ Model of an Storage Object Store Containers in cfme

    Args:
        key: key of the container.
        provider: provider
    """
    key = attr.ib()
    provider = attr.ib()
    # TODO add create method after BZ 1490320 fix

    @property
    def name(self):
        # Note: name attribute needs for custom button event navigation
        return self.key


@attr.s
class ObjectStoreContainerCollection(BaseCollection):
    """Collection object for :py:class:'cfme.storage.object_store_container.ObjectStoreContainer'
    """

    ENTITY = ObjectStoreContainer

    @property
    def manager(self):
        coll = self.appliance.collections.object_managers.filter(
            {"provider": self.filters.get('provider')}
        )
        # For each provider has single object type storage manager
        return coll.all()[0]

    def all(self):
        """returning all containers objects for respective Cloud Provider"""

        # TODO(ndhandre): Need to implement with REST.

        view = navigate_to(self, 'All')

        containers = []
        try:
            for item in view.entities.elements.read():
                if self.filters.get('provider').name in item['Cloud Provider']:
                    containers.append(self.instantiate(key=item['Key'],
                                                       provider=self.filters.get('provider')))
        except NoSuchElementException:
            logger.warning('The containers table is probably not present or empty')

        return containers


@navigator.register(ObjectStoreContainerCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ObjectStoreContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select(
            'Storage', 'Object Storage', 'Object Store Containers')


@navigator.register(ObjectStoreContainer, 'Details')
class Details(CFMENavigateStep):
    VIEW = ObjectStoreContainerDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(key=self.obj.key, surf_pages=True).click()
        except ItemNotFound:
            raise ItemNotFound(f'Could not locate container {self.obj.key}')
