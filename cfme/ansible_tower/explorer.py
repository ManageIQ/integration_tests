import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import Button
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class TowerExplorerAccordion(View):
    @View.nested
    class providers(Accordion):  # noqa
        ACCORDION_NAME = 'Providers'
        tree = ManageIQTree()

    @View.nested
    class configured_systems(Accordion):  # noqa
        ACCORDION_NAME = 'Configured Systems'
        tree = ManageIQTree()

    @View.nested
    class job_templates(Accordion):  # noqa
        ACCORDION_NAME = VersionPicker({Version.lowest(): 'Job Templates', '5.10': 'Templates'})
        tree = ManageIQTree()


class TowerExplorerProviderToolbar(View):
    reload = Button(title='Refresh this page')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerExplorerSystemJobTemplatesToolbar(View):
    reload = Button(title='Refresh this page')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerExplorerSystemJobTemplatesDetailsToolbar(View):
    refresh = Button(title='Refresh this page')
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


class TowerExplorerView(BaseLoggedInPage):
    title = Text("#explorer_title_text")
    search = View.nested(Search)
    sidebar = View.nested(TowerExplorerAccordion)

    @property
    def in_tower_explorer(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Explorer'])


class TowerExplorerProvidersAllView(TowerExplorerView):
    toolbar = View.nested(TowerExplorerProviderToolbar)

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer and
            self.title.text == 'All Ansible Tower Providers' and
            self.sidebar.providers.is_opened
        )


class TowerExplorerSystemsAllView(TowerExplorerView):
    toolbar = View.nested(TowerExplorerSystemJobTemplatesToolbar)

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer and
            self.title.text == 'All Ansible Tower Configured Systems' and
            self.sidebar.configured_systems.is_opened
        )


class TowerExplorerJobTemplatesAllView(TowerExplorerView):
    toolbar = View.nested(TowerExplorerSystemJobTemplatesToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer
            and self.title.text == "All Ansible Tower Templates"
            and self.sidebar.job_templates.is_opened
        )


class TowerExplorerJobTemplateDetailsEntities(View):
    properties = SummaryTable(title="Properties")
    variables = SummaryTable(title="Variables")
    smart_management = SummaryTable(title="Smart Management")


class TowerExplorerJobTemplateDetailsView(TowerExplorerView):
    toolbar = View.nested(TowerExplorerSystemJobTemplatesDetailsToolbar)
    entities = View.nested(TowerExplorerJobTemplateDetailsEntities)

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer
            and self.title.text
            == 'Job Template (Ansible Tower) "{}"'.format(self.context["object"].name)
            and self.sidebar.job_templates.is_opened
        )


class TowerCreateServiceDialogFromTemplateView(TowerExplorerView):
    dialog_name = TextInput('dialog_name')
    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer
            and self.title.text
            == 'Adding a new Service Dialog from "{}"'.format(self.context['object'].name)
            and self.sidebar.job_templates.is_opened
        )


@attr.s
class AnsibleTowerProvider(BaseEntity):
    pass


@attr.s
class AnsibleTowerProvidersCollection(BaseCollection):
    ENTITY = AnsibleTowerProvider


@attr.s
class AnsibleTowerSystem(BaseEntity):
    pass


@attr.s
class AnsibleTowerSystemsCollection(BaseCollection):
    ENTITY = AnsibleTowerSystem


@attr.s
class AnsibleTowerJobTemplate(BaseEntity, Taggable):
    name = attr.ib()

    def create_service_dailog(self, name):
        view = navigate_to(self, "CreateServiceDialog")
        changes = view.fill({"dialog_name": name})
        if changes:
            view.save_button.click()
            return self.appliance.collections.service_dialogs.instantiate(label=name)
        else:
            view.cancel_button.click()


@attr.s
class AnsibleTowerJobTemplatesCollection(BaseCollection, TaggableCollection):
    ENTITY = AnsibleTowerJobTemplate

    def all(self):
        """Return entities for all items in Ansible Job templates collection"""
        view = navigate_to(self, "All")
        for row in view.entities.elements:
            if 'Job Template' in row.type.text:
                return self.instantiate(template_name=row.name.text)
        # return [self.instantiate(e) for e in view.entities.all_entity_names]


@navigator.register(Server, "AnsibleTowerExplorer")
class AnsibleTowerExplorer(CFMENavigateStep):
    VIEW = TowerExplorerProvidersAllView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')
        self.view.sidebar.providers.tree.click_path('All Ansible Tower Providers')


@navigator.register(AnsibleTowerProvidersCollection, 'All')
class AnsibleTowerExplorerProvidersAll(CFMENavigateStep):
    VIEW = TowerExplorerProvidersAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AnsibleTowerExplorer')

    def step(self, *args, **kwargs):
        self.view.sidebar.providers.tree.click_path('All Ansible Tower Providers')


@navigator.register(AnsibleTowerSystemsCollection, 'All')
class TowerExplorerSystemAll(CFMENavigateStep):
    VIEW = TowerExplorerSystemsAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AnsibleTowerExplorer')

    def step(self, *args, **kwargs):
        self.view.sidebar.configured_systems.tree.click_path('All Ansible Tower Configured Systems')


@navigator.register(AnsibleTowerJobTemplatesCollection, 'All')
class TowerExplorerJobTemplatesAll(CFMENavigateStep):
    VIEW = TowerExplorerJobTemplatesAllView
    prerequisite = NavigateToAttribute('appliance.server', 'AnsibleTowerExplorer')

    def step(self, *args, **kwargs):
        self.view.sidebar.job_templates.tree.click_path('All Ansible Tower Templates')


@navigator.register(AnsibleTowerJobTemplate, 'Details')
class TowerExplorerJobTemplateDetails(CFMENavigateStep):
    VIEW = TowerExplorerJobTemplateDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise ItemNotFound('Could not locate template "{}"'.format(self.obj.name))
        row.click()


@navigator.register(AnsibleTowerJobTemplate, 'CreateServiceDialog')
class TowerCreateServiceDialogFromTemplate(CFMENavigateStep):
    VIEW = TowerCreateServiceDialogFromTemplateView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select(
            'Create Service Dialog from this Template')
