# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
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
from cfme.common import TagPageView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
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
    download = Button(title='Download summary in PDF format')


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
        expected_title = '{} (Summary)'.format(self.context['object'].key)

        return (
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

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

    def all(self):
        """returning all containers objects for respective Cloud Provider"""
        view = navigate_to(self, 'All')

        containers = []

        # ToDo: use all_entity_names method as JS API issue (#2898) resolve.
        view.entities.elements.wait_displayed()
        for item in view.entities.elements.read():
            if self.filters.get('provider').name in item['Cloud Provider']:
                containers.append(self.instantiate(key=item['Key'],
                                                   provider=self.filters.get('provider')))
        return containers


@navigator.register(ObjectStoreContainerCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ObjectStoreContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select(
            'Storage', 'Object Storage', 'Object Store Containers')

    def resetter(self, *args, **kwargs):
        self.view.toolbar.view_selector.select("List View")


@navigator.register(ObjectStoreContainer, 'Details')
class Details(CFMENavigateStep):
    VIEW = ObjectStoreContainerDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            # ToDo: use get_entity method as JS API issue (#2898) resolve.
            row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                self.prerequisite_view.entities.elements, key=self.obj.key)
            row.click()

        except NoSuchElementException:
            raise ItemNotFound('Could not locate container {}'.format(self.obj.key))


@navigator.register(ObjectStoreContainer, 'EditTagsFromDetails')
class ObjectDetailEditTag(CFMENavigateStep):
    """ This navigation destination help to Taggable"""
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
