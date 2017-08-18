# -*- coding: utf-8 -*-
"""Page model for Automation/Anisble/Playbooks"""
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, View
from widgetastic_manageiq import (
    BaseEntitiesView,
    BaseListEntity,
    BaseQuadIconEntity,
    BaseTileIconEntity,
    BreadCrumb,
    ItemsToolBarViewSelector,
    NonJSBaseEntity,
    PaginationPane,
    SummaryTable,
)
from widgetastic_patternfly import Button, Dropdown, FlashMessages

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep


class PlaybookBaseView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@class, "flash_text_div") or @id="flash_text_div"]')
    title = Text(locator='.//div[@id="main-content"]//h1')

    @property
    def in_ansible_playbooks(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Ansible", "Playbooks"]
        )


class PlaybooksToolbar(View):
    view_selector = View.nested(ItemsToolBarViewSelector)
    download = Dropdown("Download")


class PlaybookGridIconEntity(BaseQuadIconEntity):
    pass


class PlaybookTileIconEntity(BaseTileIconEntity):
    pass


class PlaybookListEntity(BaseListEntity):
    pass


class PlaybookEntity(NonJSBaseEntity):
    grid_entity = PlaybookGridIconEntity
    tile_entity = PlaybookTileIconEntity
    list_entity = PlaybookListEntity


class PlaybookDetailsEntities(View):
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")
    smart_management = SummaryTable(title="Smart Management")


class PlaybookDetailsView(PlaybookBaseView):
    download_button = Button(title="Download summary in PDF format")
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    entities = View.nested(PlaybookDetailsEntities)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == "{} (Summary)".format(self.context["object"].name)
        )


class PlaybookEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""

    @property
    def entity_class(self):
        return PlaybookEntity


class PlaybooksView(PlaybookBaseView):
    toolbar = View.nested(PlaybooksToolbar)
    paginator = View.nested(PaginationPane)
    including_entities = View.include(PlaybookEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_playbooks and
            self.title.text == "Playbooks (Embedded Ansible)"
        )


class PlaybooksCollection(Navigatable):
    """Collection object for the :py:class:`Playbook`."""

    def __init__(self, parent_repository):
        self.parent = parent_repository
        Navigatable.__init__(self, appliance=parent_repository.appliance)

    def instantiate(self, name, repository):
        return Playbook(name, repository, self)

    def all(self):
        view = navigate_to(Server, "AnsiblePlaybooks")
        playbooks = []
        for entity in view.entities.get_all(surf_pages=True):
            if entity.data["Repository"] == self.parent.name:
                playbooks.append(
                    self.instantiate(entity.data["Name"], entity.data["Repository"])
                )
        return playbooks


class Playbook(Navigatable):
    """A class representing one Embedded Ansible playbook in the UI."""

    def __init__(self, name, repository, collection):
        Navigatable.__init__(self, appliance=collection.appliance)
        self.collection = collection
        self.name = name
        self.repository = repository

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
            return True
        except ItemNotFound:
            return False


@navigator.register(Server)
class AnsiblePlaybooks(CFMENavigateStep):
    VIEW = PlaybooksView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.prerequisite_view.navigation.select("Automation", "Ansible", "Playbooks")


@navigator.register(Playbook)
class Details(CFMENavigateStep):
    VIEW = PlaybookDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "AnsiblePlaybooks")

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()
