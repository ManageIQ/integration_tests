import attr
from navmazing import NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
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
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
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
    title = Text('//div[@id="main-content"]//h1')
    search = View.nested(Search)
    toolbar = View.nested(TowerJobsToolbar)
    paginator = PaginationPane()
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def in_jobs(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Automation', 'Ansible Tower', 'Jobs']
        )

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class TowerJobsDefaultView(TowerJobsView):
    @property
    def is_displayed(self):
        return (
            self.in_jobs and
            self.title.text == 'Ansible Tower Jobs'
        )


class AnsibleTowerJobsDetailsView(TowerJobsView):
    @View.nested
    class entities(View):  # noqa
        """ Represents details page when it's switched to Summary/Table view """
        properties = SummaryTable(title="Properties")
        relationships = SummaryTable(title="Relationships")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        """Is this view being displayed?"""
        return self.title.text == '{} (Summary)'.format(self.context['object'].template_name)


@attr.s
class TowerJob(BaseEntity):
    template_name = attr.ib()

    @property
    def status(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of("Status")

    def delete(self):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Job', handle_alert=True)
        view.flash.assert_no_error()

    def is_job_successful(self):
        return True if self.status == "successful" else False

    def wait_for_completion(self, num_sec=1200, delay=10):
        def last_status():
            logger.info("Last status message in UI: '{}'".format(self.status))

        wait_for(self.is_job_successful, num_sec=num_sec, delay=delay, fail_func=last_status,
                 message="Job finished")


@attr.s
class TowerJobsCollection(BaseCollection):
    ENTITY = TowerJob

    def all(self):
        view = navigate_to(self, 'All')
        return [
            self.instantiate(template_name=e.data["template_name"])
            for e in view.entities.get_all(surf_pages=True)
        ]

    def status(self, template_name):
        """Get status of a specific job from the All page."""
        view = navigate_to(self, 'All')
        for e in view.entities.get_all(surf_pages=True):
            if e.data["template_name"] == template_name:
                return e.data["status"]
        raise NoSuchElementException("No job named {}".format(template_name))

    def delete_all(self):
        view = navigate_to(self, 'All')
        view.paginator.check_all()
        view.configuration.item_select('Remove Jobs', handle_alert=True)
        view.flash.assert_no_error()

    def is_job_successful(self, template_name):
        try:
            return True if self.status(template_name) == "successful" else False
        except NoSuchElementException:
            return None

    @property
    def are_all_jobs_successful(self):
        return all([self.is_job_successful(job.template_name) for job in self.all()])


@navigator.register(TowerJobsCollection, 'All')
class All(CFMENavigateStep):
    VIEW = TowerJobsDefaultView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Automation', 'Ansible Tower', 'Jobs')


@navigator.register(TowerJob)
class Details(CFMENavigateStep):
    VIEW = AnsibleTowerJobsDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(template_name=self.obj.template_name).click()
