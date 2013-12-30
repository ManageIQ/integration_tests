from pages.base import Base


class Explorer(Base):
    _page_title = 'CloudForms Management Engine: Control'

    @property
    def accordion(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import NewTreeAccordionItem
        return Accordion(self.testsetup, NewTreeAccordionItem)

    def click_on_events_accordion(self):
        self.accordion.accordion_by_name("Events").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.events import Events
        return Events(self.testsetup)

    def click_on_actions_accordion(self):
        self.accordion.accordion_by_name("Actions").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.actions import Actions
        return Actions(self.testsetup)

    def click_on_policies_accordion(self):
        self.accordion.accordion_by_name("Policies").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.policies import Policies
        return Policies(self.testsetup)

    def click_on_conditions_accordion(self):
        self.accordion.accordion_by_name("Conditions").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.conditions import Conditions
        return Conditions(self.testsetup)

    def click_on_policy_profiles_accordion(self):
        self.accordion.accordion_by_name("Policy Profiles").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.policy_profiles import PolicyProfiles
        return PolicyProfiles(self.testsetup)

    def click_on_alert_profiles_accordion(self):
        self.accordion.accordion_by_name("Alert Profiles").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.alert_profiles import AlertProfiles
        return AlertProfiles(self.testsetup)

    def click_on_alerts_accordion(self):
        self.accordion.accordion_by_name("Alerts").click()
        self._wait_for_results_refresh()
        from pages.control_subpages.explorer_subpages.alerts import Alerts
        return Alerts(self.testsetup)
