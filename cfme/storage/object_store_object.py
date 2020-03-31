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
from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.providers import get_crud_by_name
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class ObjectStoreObjectToolbar(View):
    """The toolbar on the Object Store Object page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ObjectStoreObjectDetailsToolbar(View):
    """The toolbar on the Object Store Object detail page"""
    policy = Dropdown('Policy')
    download = Button(title='Print or export summary')


class ObjectStoreObjectDetailsEntities(View):
    """The entities on the Object Store Object detail page"""
    breadcrumb = BreadCrumb()
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class ObjectStoreObjectDetailsSidebar(View):
    """The sidebar on the Object Store Object details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class ObjectStoreObjectView(BaseLoggedInPage):
    """A base view for all the Object Store Object pages"""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_object(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Storage', 'Object Storage',
                                                   'Object Store Objects'])


class ObjectStoreObjectAllView(ObjectStoreObjectView):
    """The all Object Store Object page"""
    toolbar = View.nested(ObjectStoreObjectToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_object and
            self.title.text == 'Cloud Object Store Objects')

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class ObjectStoreObjectDetailsView(ObjectStoreObjectView):
    """The detail Object Store Object page"""
    @property
    def is_displayed(self):
        obj = self.context['object']

        return (
            self.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb
        )

    toolbar = View.nested(ObjectStoreObjectDetailsToolbar)
    sidebar = View.nested(ObjectStoreObjectDetailsSidebar)
    entities = View.nested(ObjectStoreObjectDetailsEntities)


@attr.s
class ObjectStoreObject(BaseEntity, Taggable):
    """ Model of an Storage Object Store Object in cfme

    Args:
        key: key of the object.
        provider: provider
    """
    key = attr.ib()
    provider = attr.ib()

    @property
    def name(self):
        return self.key


@attr.s
class ObjectStoreObjectCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.storage.object_store_object.ObjStoreObject' """

    ENTITY = ObjectStoreObject

    @property
    def manager(self):
        coll = self.appliance.collections.object_managers.filter(
            {"provider": self.filters.get('provider')}
        )
        # For each provider has single object type storage manager
        return coll.all()[0]

    def all(self):
        """returning all Object Store Objects"""
        view = navigate_to(self, 'All')
        view.entities.paginator.set_items_per_page(500)
        objects = []

        try:
            if 'provider'in self.filters:
                for item in view.entities.elements.read():
                    if self.filters['provider'].name in item['Cloud Provider']:
                        objects.append(self.instantiate(key=item['Key'],
                                                        provider=self.filters['provider']))
            else:
                for item in view.entities.elements.read():
                    provider_name = item['Cloud Provider'].split()[0]
                    provider = get_crud_by_name(provider_name)
                    objects.append(self.instantiate(key=item['Key'], provider=provider))
            return objects

        except NoSuchElementException:
            return None

    def delete(self, *objects):
        view = navigate_to(self, 'All')

        for obj in objects:
            try:
                view.entities.get_entity(key=obj.key, surf_pages=True).ensure_checked()
            except ItemNotFound:
                raise ItemNotFound(f'Could not locate object {obj.key}')

        view.toolbar.configuration.item_select('Remove Object Storage Objects', handle_alert=True)
        view.flash.assert_no_error()


@navigator.register(ObjectStoreObjectCollection, 'All')
class ObjectStoreObjectAll(CFMENavigateStep):
    VIEW = ObjectStoreObjectAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select(
            'Storage', 'Object Storage', 'Object Store Objects')


@navigator.register(ObjectStoreObject, 'Details')
class ObjectStoreObjectDetails(CFMENavigateStep):
    VIEW = ObjectStoreObjectDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(key=self.obj.key, surf_pages=True).click()
        except ItemNotFound:
            raise ItemNotFound(f'Could not locate object {self.obj.key}')
