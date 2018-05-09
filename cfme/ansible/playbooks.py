# -*- coding: utf-8 -*-
"""Page model for Automation/Anisble/Playbooks"""
import attr
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, View
from widgetastic_patternfly import Button, Dropdown
from widgetastic_manageiq import (
    BaseEntitiesView,
    BreadCrumb,
    ItemsToolBarViewSelector,
    PaginationPane,
    SummaryTable,
)

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.common import Taggable, TagPageView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep


class PlaybookBaseView(BaseLoggedInPage):
    title = Text(locator='.//div[@id="main-content"]//h1')

    @property
    def in_ansible_playbooks(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Ansible", "Playbooks"]
        )


class PlaybooksToolbar(View):
    view_selector = View.nested(ItemsToolBarViewSelector)
    policy = Dropdown('Policy')
    download = Dropdown("Download")


class PlaybookDetailsEntities(View):
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")
    smart_management = SummaryTable(title="Smart Management")


class PlaybookDetailsView(PlaybookBaseView):

    @View.nested
    class toolbar(View):   # noqa
        configuration = Dropdown("Configuration")
        policy = Dropdown(text='Policy')
        download_button = Button(title="Download summary in PDF format")

    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    entities = View.nested(PlaybookDetailsEntities)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_repositories and
            self.title.text == "{} (Summary)".format(self.context["object"].name)
        )


class PlaybooksView(PlaybookBaseView):
    toolbar = View.nested(PlaybooksToolbar)
    paginator = View.nested(PaginationPane)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_playbooks and
            self.title.text == "Playbooks (Embedded Ansible)"
        )


@attr.s
class Playbook(BaseEntity, Taggable):
    """A class representing one Embedded Ansible playbook in the UI."""

    name = attr.ib()
    repository = attr.ib()

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
            return True
        except ItemNotFound:
            return False


@attr.s
class PlaybooksCollection(BaseCollection):
    """Collection object for the :py:class:`Playbook`."""

    ENTITY = Playbook

    def all(self):
        view = navigate_to(self.appliance.server, "AnsiblePlaybooks")
        playbooks = []
        parent = self.filters.get('parent', None)
        for _ in view.entities.paginator.pages():
            for row in view.entities.elements:
                if (parent and row["Repository"].text == parent.name) or not parent:
                    playbooks.append(self.instantiate(row["Name"].text, row["Repository"].text))
        return playbooks


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
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Playbook, 'EditTags')
class EditTagsFromListCollection(CFMENavigateStep):
    VIEW = TagPageView

    prerequisite = NavigateToAttribute("appliance.server", "AnsiblePlaybooks")

    def step(self):
        self.prerequisite_view.entities.get_entity(surf_pages=True, name=self.obj.name).check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
