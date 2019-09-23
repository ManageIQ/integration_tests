import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class TowerJobsToolbar(View):
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class TowerJobsView(BaseLoggedInPage):
    search = View.nested(Search)
    toolbar = View.nested(TowerJobsToolbar)
    paginator = PaginationPane()
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def in_jobs(self):
        # title = 'Ansible Tower Jobs'
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Jobs'])

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class TowerJobsDefaultView(TowerJobsView):
    title = Text('//div[@id="main-content"]//h1')

    @property
    def is_displayed(self):
        return (
            self.in_jobs and
            self.title.text == 'Ansible Tower Jobs'
        )


class AnsibleTowerJobsDetailsView(View):
    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        title = '{} (Summary)'.format(self.obj.name)
        return self.title.text == title


@attr.s
class TowerJobs(BaseEntity):
    template_name = attr.ib()

    @property
    def status(self):
        view = navigate_to(self.parent, 'All')
        for row in view.entities.elements:
            if row.template_name.text == self.template_name:
                return row.status.text
        return ''

    def delete(self):
        view = navigate_to(self.parent, 'Details')
        view.configuration.item_select('Remove Jobs', handle_alert=True)


@attr.s
class TowerJobsCollection(BaseCollection):
    ENTITY = TowerJobs

    def all(self):
        id = self.filters.get('id', 0)
        temp_name = self.filters.get('temp_name')
        view = navigate_to(self, 'All')
        jobs = []

        for entity in [entity for entity in view.entities.get_all(surf_pages=True)]:
            if int(entity.id) > int(id) and temp_name == row.template_name:
                jobs.append(self.instantiate(template_name=temp_name))

        return jobs

        @property
        def is_all_finished(self):
            jobs = self.all()
            all_success = True
            for job in jobs:
                if job.status == "successfull":
                    continue
                else:
                    all_success = False
            return all_success

        def delete_all(self):
            view = navigate_to(self, 'All')
            view.paginator.check_all()
            view.configuration.item_select('Remove Jobs', handle_alert=True)

        @property
        def is_job_finished(self):
            job = self.first_by_date()
            if job.status == "successful":
                return True
            else:
                return False


@navigator.register(TowerJobsCollection, 'All')
class All(CFMENavigateStep):
    VIEW = TowerJobsDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Jobs')


@navigator.register(TowerJobs)
class Details(CFMENavigateStep):
    VIEW = AnsibleTowerJobsDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.template_name).click()
