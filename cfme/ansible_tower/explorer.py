from navmazing import NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import Dropdown
from widgetastic.utils import VersionPick, Version

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from widgetastic_manageiq import Search, ItemsToolBarViewSelector, Button, Accordion, ManageIQTree


class TowerExplorerAccordion(View):
    @View.nested
    class tower_explorer_providers(Accordion):  # noqa
        ACCORDION_NAME = 'Providers'
        tree = ManageIQTree()

    @View.nested
    class tower_explorer_systems(Accordion):  # noqa
        ACCORDION_NAME = 'Configured Systems'
        tree = ManageIQTree()

    @View.nested
    class tower_explorer_job_templates(Accordion):  # noqa
        ACCORDION_NAME = 'Job Templates'
        tree = ManageIQTree()


class TowerExplorerProviderToolbar(View):
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerExplorerSystemJobTemplatesToolbar(View):
    reload = Button(title=VersionPick({Version.lowest(): 'Reload current display',
                                       '5.9': 'Refresh this page'}))
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerExplorerView(BaseLoggedInPage):
    search = View.nested(Search)
    sidebar = View.nested(TowerExplorerAccordion)

    @property
    def in_tower_explorer(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Explorer'])


class TowerExplorerProviderView(TowerExplorerView):
    toolbar = View.nested(TowerExplorerProviderToolbar)


class TowerExplorerSystemView(TowerExplorerView):
    search = View.nested(Search)
    toolbar = View.nested(TowerExplorerSystemJobTemplatesToolbar)


class TowerExplorerJobTemplatesView(TowerExplorerView):
    search = View.nested(Search)
    toolbar = View.nested(TowerExplorerSystemJobTemplatesToolbar)


class TowerExplorerProviderDefaultView(TowerExplorerProviderView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer and
            self.title.text == 'All Ansible Tower Providers' and
            self.sidebar.tower_explorer_providers.is_opened
        )


class TowerExplorerSystemDefaultView(TowerExplorerProviderView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer and
            self.title.text == 'All Ansible Tower Configured Systems' and
            self.sidebar.tower_explorer_systems.is_opened
        )


class TowerExplorerJobTemplatesDefaultView(TowerExplorerProviderView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_tower_explorer and
            self.title.text == 'All Ansible Tower Job Templates' and
            self.sidebar.tower_explorer_job_templates.is_opened
        )


class TowerExplorerProvider(Navigatable):
    pass


class TowerExplorerSystem(Navigatable):
    pass


class TowerExplorerJobTemplates(Navigatable):
    pass


@navigator.register(TowerExplorerProvider, 'All')
class TowerExplorerProviderAll(CFMENavigateStep):
    VIEW = TowerExplorerProviderDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')
        self.view.search.clear_simple_search()


@navigator.register(TowerExplorerSystem, 'All')
class TowerExplorerSystemAll(CFMENavigateStep):
    VIEW = TowerExplorerSystemDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')
        self.view.sidebar.tower_explorer_systems.tree.click_path(
            'All Ansible Tower Configured Systems')
        self.view.search.clear_simple_search()


@navigator.register(TowerExplorerJobTemplates, 'All')
class TowerExplorerJobTemplatesAll(CFMENavigateStep):
    VIEW = TowerExplorerJobTemplatesDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Explorer')
        self.view.sidebar.tower_explorer_job_templates.tree.click_path(
            'All Ansible Tower Job Templates')
        self.view.search.clear_simple_search()
