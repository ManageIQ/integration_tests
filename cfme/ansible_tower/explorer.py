import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, View
from widgetastic_patternfly import Dropdown
from widgetastic_manageiq import Search, ItemsToolBarViewSelector, Button, Accordion, ManageIQTree

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.utils.version import Version, VersionPicker


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

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer and
            self.title.text == VersionPicker({Version.lowest(): 'All Ansible Tower Job Templates',
                '5.10': 'All Ansible Tower Templates'}).pick(self.browser.product_version) and
            self.sidebar.job_templates.is_opened
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
class AnsibleTowerJobTemplate(BaseEntity):
    pass


@attr.s
class AnsibleTowerJobTemplatesCollection(BaseCollection):
    ENTITY = AnsibleTowerJobTemplate


@navigator.register(Server, 'AnsibleTowerExplorer')
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
        self.view.sidebar.job_templates.tree.click_path(VersionPicker({Version.lowest():
            'All Ansible Tower Job Templates', '5.10': 'All Ansible Tower Templates'}).pick(
            self.view.browser.product_version))
