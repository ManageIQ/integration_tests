# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_patternfly import BreadCrumb, Button, Dropdown
from widgetastic.widget import View, Text, NoSuchElementException

from cfme.base.login import BaseLoggedInPage
from cfme.common import TaggableCollection, Taggable
from cfme.exceptions import ItemNotFound, VolumeTypeNotFoundError
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.storage.volume import VolumeToolbar
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.update import Updateable
from widgetastic_manageiq import Search, BaseEntitiesView, SummaryTable


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
    download = Button('Download summary in PDF format')


class VolumeTypeDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable('Properties')
    relationships = SummaryTable('Relationships')
    smart_management = SummaryTable('Smart Management')


class VolumeTypeDetailsView(VolumeTypeView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        try:
            provider = self.entities.relationships.get_text_of('Cloud Provider')
        except NameError:
            provider = self.entities.relationships.get_text_of('Parent Cloud Provider')
        return (self.in_volume_type and
                self.entities.title.text == expected_title and
                self.entities.breadcrumb.active_location == expected_title and
                provider == self.context['object'].provider.name)

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

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except VolumeTypeNotFoundError:
            return False


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
            raise VolumeTypeNotFoundError('Volume Type {} not found'.format(self.obj.name))
