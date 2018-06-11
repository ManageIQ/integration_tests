from navmazing import NavigateToAttribute
from widgetastic.widget import Text, View
from widgetastic_patternfly import Dropdown
from widgetastic_manageiq import Search, ItemsToolBarViewSelector

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class TowerJobsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerJobsView(BaseLoggedInPage):
    search = View.nested(Search)
    toolbar = View.nested(TowerJobsToolbar)

    @property
    def in_jobs(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Jobs'])


class TowerJobsDefaultView(TowerJobsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_jobs and
            self.title.text == 'Ansible Tower Jobs'
        )


class TowerJobs(Navigatable):
    pass


@navigator.register(TowerJobs, 'All')
class All(CFMENavigateStep):
    VIEW = TowerJobsDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Jobs')
