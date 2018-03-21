from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.pretty import Pretty
from widgetastic_manageiq import Table, ItemsToolBarViewSelector
from widgetastic.widget import View, Text

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_patternfly import Dropdown


class AnsibleJobsToolbarView(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')


class AnsibleTowerJobsView(View):
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(AnsibleJobsToolbarView)
    items = Table('//div[@class="miq-data-table"]/table')
    view_selector = View.nested(ItemsToolBarViewSelector)

    @property
    def is_displayed(self):
        title = "Ansible Tower Jobs"
        return (self.title.text == title and self.logged_is_as_current_user and
                self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Jobs'])


class AnsibleTowerJobsDetailsView(View):
    toolbar = View.nested(AnsibleJobsToolbarView)

    @property
    def is_displayed(self):
        title = "{} (Summary)".format(self.obj.name)
        return self.title.text == title


class AnsibleTowerJobs(Pretty, Navigatable):
    def __init__(self, name=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name

    def delete(self):
        view = navigate_to(AnsibleTowerJobs, "All")
        view.items.row(template_name=self.name).click()
        view.toolbar.configuration.item_select("Remove Jobs")
        pass


@navigator.register(AnsibleTowerJobs)
class All(CFMENavigateStep):
    VIEW = AnsibleTowerJobsView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Jobs')
        self.view.view_selector.select('List View')


@navigator.register(AnsibleTowerJobs)
class Details(CFMENavigateStep):
    VIEW = AnsibleTowerJobsDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.items.row(template_name=self.obj.name).click()
