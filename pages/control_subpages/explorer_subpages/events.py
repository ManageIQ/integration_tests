from selenium.webdriver.common.by import By
from pages.control_subpages.explorer import Explorer


class Events(Explorer):
    _events_table = (By.CSS_SELECTOR, "div#event_list_div fieldset table tbody")
    _event_row_locator = (By.XPATH, "tr")
    _event_items_locator = (By.XPATH, "td")
    
    def show_all_events(self):
        """ Show back the screen with all events in the table.

        """
        self.accordion.current_content.find_node_by_name("All Events").click()
        self._wait_for_results_refresh()

    @property
    def table(self):
        return self.selenium.find_element(*self._events_table)

    @property
    def root(self):
        return self.table.find_elements(*self._event_row_locator)

    @property
    def events(self):
        self.show_all_events()
        elements = [element.find_elements(*self._event_items_locator) for element in self.root]
        events = [(img, event_desc.text) for img, event_desc in elements]
        return events

    def find_event(self, name):
        for element, event_name in self.events:
            if event_name.strip() == name.strip():
                return element
        raise Exception("No event with name '%s' found!" % name)

    def get_event(self, name):
        self.find_event(name).click()
        self._wait_for_results_refresh()
        return Event(self.testsetup)

    @property
    def events_list(self):
        return [event[1] for event in self.events]

    @property
    def print_events_list(self):
        # for generating default events list
        for event in self.events:
            print "'%s'," % event[1]


class Event(Events):
    """ This class represents a screen with details of the event

    """
    _refresh_locator = (By.XPATH, "//*[@id='miq_alone']/img")
    _ev_grp_locator = (By.XPATH, "//*[@id=\"event_info_div\"]/fieldset[1]/table/tbody/tr/td[2]")
    _assigned_table_locator = (By.XPATH, "//*[@id=\"event_info_div\"]/fieldset[2]/table")
    _policy_rows_locator = (By.XPATH, "./tbody/tr/td[2]")

    @property
    def refresh_button(self):
        """ Refresh button.

        Used for refreshing the page.
        """
        return self.selenium.find_element(*self._refresh_locator)

    @property
    def event_group_text(self):
        """ Event group description.

        """
        return self.selenium.find_element(*self._ev_grp_locator)

    @property
    def event_group(self):
        """ Basic Information / Event group

        """
        return self.event_group_text.text.strip()

    def click_on_refresh(self):
        """ Refreshes the page

        Clicks on a refresh button and waits until refresh is finished.
        """
        self.refresh_button.click()
        self._wait_for_results_refresh()

    @property
    def assigned_policies(self):
        """ Lists names of assigned policies

        @todo: Click on the policies?
        """
        if not self.is_element_present(*self._assigned_table_locator):
            return []
        else:
            table = self.selenium.find_element(*self._assigned_table_locator)
            policies = table.find_elements(*self._policy_rows_locator)
            return [policy.text.strip() for policy in policies]
