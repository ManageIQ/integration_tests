# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.storage.volume import VolumeToolbar
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import Updateable
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class VolumeTypeView(BaseLoggedInPage):
    @property
    def in_volume_type(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Storage', 'Block Storage', 'Volume Types'])


class VolumeTypeAllView(VolumeTypeView):
    toolbar = View.nested(VolumeToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_volume_type and
            self.entities.title.text == 'Cloud Volume Types'
        )


class VolumeTypeDetailsToolbar(View):
    policy = Dropdown('Policy')
    download = Button('Print or export summary')


class VolumeTypeDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class VolumeTypeDetailsView(VolumeTypeView):
    @property
    def is_displayed(self):
        obj = self.context['object']
        try:
            provider = self.entities.relationships.get_text_of('Cloud Provider')
        except NameError:
            provider = self.entities.relationships.get_text_of('Parent Cloud Provider')
        return (self.in_volume_type and
                self.entities.title.text == obj.expected_details_title and
                self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb and
                provider == obj.provider.name)

    toolbar = View.nested(VolumeTypeDetailsToolbar)
    entities = View.nested(VolumeTypeDetailsEntities)


@attr.s
class VolumeType(BaseEntity, Updateable, Taggable):
    name = attr.ib()
    provider = attr.ib()

    def refresh(self):
        """Refresh provider relationships and browser"""
        self.provider.refresh_provider_relationships()
        self.browser.refresh()


@attr.s
class VolumeTypeCollection(BaseCollection, TaggableCollection):
    """Collection object for :py:class:'cfme.storage.volume_type.VolumeType'. """
    ENTITY = VolumeType


@navigator.register(VolumeTypeCollection, 'All')
class VolumeTypeAll(CFMENavigateStep):
    VIEW = VolumeTypeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Storage', 'Block Storage', 'Volume Types')


@navigator.register(VolumeType, 'Details')
class VolumeTypeDetails(CFMENavigateStep):
    VIEW = VolumeTypeDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
        except ItemNotFound:
            raise ItemNotFound('Volume Type {} not found'.format(self.obj.name))
