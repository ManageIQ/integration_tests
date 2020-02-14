import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button

from cfme.common import BaseLoggedInPage
from cfme.exceptions import RestLookupError
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.services.requests import RequestsView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import SummaryForm


@attr.s
class AutomationRequest(BaseEntity):
    # TODO: Add more methods and properties as required, refer service `Request` entity

    description = attr.ib(default=None)
    message = attr.ib(default=None)

    @property
    def rest_api_entity(self):
        try:
            return self.appliance.rest_api.collections.automation_requests.get(
                description=self.description
            )
        except ValueError:
            raise RestLookupError(
                f"No automation request rest entity found matching description '{self.description}'"
            )


@attr.s
class AutomationRequestCollection(BaseCollection):
    """The appliance collection of requests"""

    ENTITY = AutomationRequest


class AutomateRequestsToolbar(View):
    """Toolbar on the requests view"""

    reload = Button(title="Refresh this page")
    delete = Button(title="Delete this Request")


class AutomateRequestsView(RequestsView):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ["Automation", "Automate", "Requests"]
            and self.title.text == "Requests"
        )


class AutomateRequestsDetailsView(BaseLoggedInPage):
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(AutomateRequestsToolbar)

    @View.nested
    class details(View):  # noqa
        request_details = SummaryForm("Request Details")

    @View.nested
    class automations_tasks(View):
        # TODO: Add a widget for Automations Tasks
        pass

    @property
    def is_displayed(self):
        description = self.context["object"].description
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ["Automation", "Automate", "Requests"]
            and self.title.text == description
            and self.breadcrumb.active_location == description
        )


@navigator.register(AutomationRequestCollection, "All")
class AutomateRequestsAll(CFMENavigateStep):
    VIEW = AutomateRequestsView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Automation", "Automate", "Requests")


@navigator.register(AutomationRequest, "Details")
class AutomateRequestsDetails(CFMENavigateStep):
    VIEW = AutomateRequestsDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        return self.prerequisite_view.table.row(description=self.obj.description).click()
