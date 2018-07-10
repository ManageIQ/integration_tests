# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text, NoSuchElementException
from widgetastic_patternfly import BreadCrumb, Button, Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.common import TagPageView, Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.providers import get_crud_by_name
from widgetastic_manageiq import (
    Accordion, BaseEntitiesView, ItemsToolBarViewSelector, ManageIQTree, SummaryTable, Search)


class ObjectStoreObjectToolbar(View):
    """The toolbar on the Object Store Object page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class ObjectStoreObjectDetailsToolbar(View):
    """The toolbar on the Object Store Object detail page"""
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


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


class ObjectStoreObjectDetailsView(ObjectStoreObjectView):
    """The detail Object Store Object page"""
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].key)

        return (
            self.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

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


@attr.s
class ObjectStoreObjectCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.storage.object_store_object.ObjStoreObject' """

    ENTITY = ObjectStoreObject

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
        # TODO: capture flash message after BZ 1497113 resolve.
        view = navigate_to(self, 'All')

        for obj in objects:
            try:
                row = view.entities.paginator.find_row_on_pages(
                    view.entities.elements, key=obj.key)
                row[0].check()
            except NoSuchElementException:
                raise ItemNotFound('Could not locate object {}'.format(obj.key))

        view.toolbar.configuration.item_select('Remove Object Storage Objects',
                                               handle_alert=True)


@navigator.register(ObjectStoreObjectCollection, 'All')
class ObjectStoreObjectAll(CFMENavigateStep):
    VIEW = ObjectStoreObjectAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select(
            'Storage', 'Object Storage', 'Object Store Objects')

    def resetter(self):
        self.view.toolbar.view_selector.select("List View")


@navigator.register(ObjectStoreObject, 'Details')
class ObjectStoreObjectDetails(CFMENavigateStep):
    VIEW = ObjectStoreObjectDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            # ToDo: use get_entity method as JS API issue (#2898) resolve.
            row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                self.prerequisite_view.entities.elements, key=self.obj.key)
            row[1].click()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate object {}'.format(self.obj.key))


@navigator.register(ObjectStoreObject, 'EditTagsFromDetails')
class ObjectStoreObjectDetailEditTag(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
