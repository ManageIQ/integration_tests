# -*- coding: utf-8 -*-

import time
from pages.cloud.instances.common import CommonComponents
from selenium.webdriver.common.by import By

class Utilization(CommonComponents):
    _interval_input_field_locator = (By.CSS_SELECTOR, "select#perf_typ")
    _daily_show_edit_field_locator = (By.CSS_SELECTOR, "select#perf_days")
    _recent_show_edit_field_locator = (By.CSS_SELECTOR, "select#perf_minutes")
    _time_zone_edit_field_locator = (By.CSS_SELECTOR, "select#time_zone")
    _compare_to_edit_field_locator = (By.CSS_SELECTOR, "select#compare_to")
    _date_edit_field_locator = (By.CSS_SELECTOR, "input#miq_date_1")
    _options_frame_locator = (By.ID, "perf_options_div")

    @property
    def options_frame(self):
        return self.selenium.find_element(*self._options_frame_locator)

    @property
    def date_field(self):
        return self.selenium.find_element(
                        *self._date_edit_field_locator)

    def fill_data(self, interval,  show, time_zone, compare_to, date):
        if(interval):
            self.select_dropdown(interval, *self._interval_input_field_locator)
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround
        if(date):
            self.date_field._parent.execute_script(
                "$j('#miq_date_1').attr('value', '%s')" % date)
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround
        if(show and interval == "Daily"):
            self.select_dropdown(show, *self._daily_show_edit_field_locator)
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround
        if (show and interval == "Most Recent Hour"):
            self.select_dropdown(show, *self._recent_show_edit_field_locator)
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround
        if(time_zone):
            self.select_dropdown(time_zone, *self._time_zone_edit_field_locator)
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround
        if(compare_to):
            self.select_dropdown(compare_to,
                    *self._compare_to_edit_field_locator)
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround
        self._wait_for_results_refresh()
        time.sleep(20) #issue 104 workaround
