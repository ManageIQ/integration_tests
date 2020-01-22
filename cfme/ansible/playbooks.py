"""Page model for Automation/Anisble/Playbooks"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import SummaryTable


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
        download = Button(title="Print or export summary")

    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    entities = View.nested(PlaybookDetailsEntities)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_playbooks and
            self.title.text == self.context["object"].expected_details_title
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

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Automation", "Ansible", "Playbooks")


@navigator.register(Playbook)
class Details(CFMENavigateStep):
    VIEW = PlaybookDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "AnsiblePlaybooks")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Playbook, 'EditTags')
class EditTagsFromListCollection(CFMENavigateStep):
    VIEW = TagPageView

    prerequisite = NavigateToAttribute("appliance.server", "AnsiblePlaybooks")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(surf_pages=True,
                                                   name=self.obj.name).ensure_checked()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
