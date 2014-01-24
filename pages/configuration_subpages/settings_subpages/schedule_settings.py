from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.taskbar.taskbar import TaskbarMixin
from selenium.webdriver.support.ui import Select
from utils.wait import wait_for
import re


class ScheduleSettingsCommon(Base, TaskbarMixin):
    _page_title = 'CloudForms Management Engine: Configuration'

    @property
    def accordion(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
        return Accordion(self.testsetup, LegacyTreeAccordionItem)


class ScheduleSettings(ScheduleSettingsCommon):
    _add_new_button_locator = (By.CSS_SELECTOR,
        "tr[title='Add a new Schedule'] > td.td_btn_txt > div")
    _edit_selected_button_locator = (By.CSS_SELECTOR,
        "tr[title='Edit the selected Schedule'] > td.td_btn_txt > div")
    _delete_selected_button_locator = (By.CSS_SELECTOR,
        "tr[title='Delete the selected Schedules from the VMDB'] > td.td_btn_txt > div")
    _enable_selected_button_locator = (By.CSS_SELECTOR,
        "tr[title='Enable the selected Schedules'] > td.td_btn_txt > div")
    _disable_selected_button_locator = (By.CSS_SELECTOR,
        "tr[title='Disable the selected Schedules'] > td.td_btn_txt > div")

    _rows_checkbox = (By.CSS_SELECTOR, ".style3 tr > td.checkbox input")
    _rows_name = (By.CSS_SELECTOR, ".style3 tr > td:nth-child(3)")

    @property
    def add_new_button(self):
        return self.selenium.find_element(*self._add_new_button_locator)

    @property
    def edit_selected_button(self):
        return self.selenium.find_element(*self._edit_selected_button_locator)

    @property
    def delete_selected_button(self):
        return self.selenium.find_element(*self._delete_selected_button_locator)

    @property
    def enable_selected_button(self):
        return self.selenium.find_element(*self._enable_selected_button_locator)

    @property
    def disable_selected_button(self):
        return self.selenium.find_element(*self._disable_selected_button_locator)

    @property
    def checkboxes_by_name(self):
        names = [line.text for line in self.selenium.find_elements(*self._rows_name)]
        checkboxes = self.selenium.find_elements(*self._rows_checkbox)
        # map checkboxes to their respective names
        checkboxes_by_name = dict(zip(names, checkboxes))
        return checkboxes_by_name

    def click_on_add_new(self):
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.add_new_button).perform()
        self._wait_for_results_refresh()
        return ScheduleSettings.NewSchedule(self.testsetup)

    def click_on_edit_selected(self):
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.edit_selected_button).perform()
        self._wait_for_results_refresh()
        return ScheduleSettings.EditSchedule(self.testsetup)

    def click_on_delete_selected(self, cancel=False):
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.delete_selected_button).perform()
        self.handle_popup(cancel)
        self._wait_for_results_refresh()
        return ScheduleSettings(self.testsetup)

    def click_on_enable_selected(self):
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.enable_selected_button).perform()
        self._wait_for_results_refresh()
        return ScheduleSettings(self.testsetup)

    def click_on_disable_selected(self):
        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.disable_selected_button).perform()
        self._wait_for_results_refresh()
        return ScheduleSettings(self.testsetup)

    def click_on_schedule(self, schedule_name):
        schedule_element = None
        for el in self.selenium.find_elements(*self._rows_name):
            if el.text.strip() == schedule_name:
                schedule_element = el
                break
        if not schedule_element:
            raise Exception("Schedule %s could not be found" % schedule_name)
        schedule_element.click()
        self._wait_for_results_refresh()
        return ScheduleSettings.ShowSchedule(self.testsetup)

    def does_schedule_exist(self, schedule_name):
        if schedule_name in self.checkboxes_by_name.iterkeys():
            return True
        return False

    def is_schedule_checked(self, schedule_name):
        return self.checkboxes_by_name[schedule_name].is_selected()

    def toggle_schedule(self, state, schedule_name):
        if state != self.is_schedule_checked(schedule_name):
            self.checkboxes_by_name[schedule_name].click()
            self._wait_for_results_refresh()

    def check_schedule(self, schedule_name):
        self.toggle_schedule(True, schedule_name)

    def check_all_schedules(self):
        for schedule_name in self.checkboxes_by_name.iterkeys():
            self.toggle_schedule(True, schedule_name)

    def uncheck_schedule(self, schedule_name):
        self.toggle_schedule(False, schedule_name)

    def uncheck_all_schedules(self):
        for schedule_name in self.checkboxes_by_name.iterkeys():
            self.toggle_schedule(False, schedule_name)

    class NewSchedule(ScheduleSettingsCommon):
        _name_field_locator = (By.CSS_SELECTOR, "input#name")
        _description_field_locator = (By.CSS_SELECTOR, "input#description")
        _active_checkbox_locator = (By.CSS_SELECTOR, "input#enabled")
        _action_type_selectbox_locator = (By.CSS_SELECTOR, "select#action_typ")

        _filter_type_selectbox_locator = (By.CSS_SELECTOR, "select#filter_typ")
        _filter_value_selectbox_locator = (By.CSS_SELECTOR, "select#filter_value")

        _log_type_selectbox_locator = (By.CSS_SELECTOR, "select#log_protocol")
        _nfs_uri_field_locator = (By.CSS_SELECTOR, "input#uri")
        _smb_uri_field_locator = (By.CSS_SELECTOR, "input#uri")
        _smb_user_id_field_locator = (By.CSS_SELECTOR, "input#log_userid")
        _smb_password_field_locator = (By.CSS_SELECTOR, "input#log_password")
        _smb_verify_field_locator = (By.CSS_SELECTOR, "input#log_verify")
        _smb_validate_button_locator = (By.CSS_SELECTOR,
            "ul#form_buttons > li > "
            "a[title='Validate the credentials by logging into the Server']")

        _timer_type_selectbox_locator = (By.CSS_SELECTOR, "select#timer_typ")
        _timer_subtype_selectbox_locator = (By.XPATH,
            "//[@id='form_timer_div']/tr[1]/span/select[starts-with(@id, 'timer_') and "
            "not(contains(@style, 'display: none'))]")
        _time_zone_selectbox_locator = (By.CSS_SELECTOR, "select#time_zone")
        _start_date_field_locator = (By.CSS_SELECTOR, "input#miq_date_1")
        _start_hour_selectbox_locator = (By.CSS_SELECTOR, "select#start_hour")
        _start_min_selectbox_locator = (By.CSS_SELECTOR, "select#start_min")

        _add_button_locator = (By.CSS_SELECTOR,
            "ul#form_buttons > li > img[title='Add']")
        _cancel_button_locator = (By.CSS_SELECTOR,
            "ul#form_buttons > li > img[title='Cancel']")

        @property
        def add_button(self):
            return self.selenium.find_element(*self._add_button_locator)

        @property
        def cancel_button(self):
            return self.selenium.find_element(*self._cancel_button_locator)

        @property
        def validate_button(self):
            return self.selenium.find_element(*self._smb_validate_button_locator)

        def toggle_checkbox(self, state, *element):
            checkbox = self.selenium.find_element(*element)
            if state:
                if not checkbox.is_selected():
                    return checkbox.click()
            else:
                if checkbox.is_selected():
                    return checkbox.click()

        def select_dropdown_substring(self, substring, *element):
            select = Select(self.selenium.find_element(*element))
            for option in select.options:
                if substring in option.text:
                    option.click()
                    return
            raise Exception('Could not select option with "%s" in text' % substring)

        def get_current_selectbox_value(self, *element):
            selectbox = Select(self.get_element(*element))
            current_value = selectbox.first_selected_option.text
            return current_value

        def is_starting_date_reset(self, expected_value='0'):
            current_value = self.get_current_selectbox_value(
                *self._start_hour_selectbox_locator)
            if current_value == expected_value:
                return True
            return False

        def will_change_time_zone(self, time_zone_to_set='UTC'):
            current_value = self.get_current_selectbox_value(
                *self._time_zone_selectbox_locator)
            if time_zone_to_set in current_value:
                return False
            return True

        def fill_data(self,
                      name="test_name",
                      description="test_description",
                      active=True,
                      action_type="vm",
                      filter_type="all",
                      filter_value="",
                      log_type="Samba",
                      uri="samba-or-nfs-fqdn-or-ip",
                      user_id="smb_only_user",
                      password="smb_only_pass",
                      verify="smb_only_pass",
                      timer_type="Monthly",
                      timer_subtype="6",
                      time_zone="UTC",
                      start_date="4/5/2063",
                      start_hour="1",
                      start_min="45"):
            self.fill_field_by_locator(name, *self._name_field_locator)
            self.fill_field_by_locator(description, *self._description_field_locator)
            self.toggle_checkbox(active, *self._active_checkbox_locator)
            self.select_dropdown_by_value(action_type, *self._action_type_selectbox_locator)
            self._wait_for_results_refresh()
            if action_type == 'db_backup':
                self.select_dropdown_by_value(log_type, *self._log_type_selectbox_locator)
                if log_type == 'Samba':
                    self._wait_for_visible_element(*self._smb_uri_field_locator)
                    self.fill_field_by_locator(uri, *self._smb_uri_field_locator)
                    self.fill_field_by_locator(user_id, *self._smb_user_id_field_locator)
                    self.fill_field_by_locator(password, *self._smb_password_field_locator)
                    self.fill_field_by_locator(verify, *self._smb_verify_field_locator)
                    self._wait_for_visible_element(*self._smb_validate_button_locator)
                elif log_type == 'Network File System':
                    self._wait_for_visible_element(*self._nfs_uri_field_locator)
                    self.fill_field_by_locator(uri, *self._nfs_uri_field_locator)
                else:
                    raise Exception("Unknown database backup type")
            else:
                self.select_dropdown_by_value(filter_type, *self._filter_type_selectbox_locator)
                if filter_value:
                    self._wait_for_visible_element(*self._filter_value_selectbox_locator)
                    self.select_dropdown_by_value(
                        filter_value, *self._filter_value_selectbox_locator)
            self.select_dropdown_by_value(timer_type, *self._timer_type_selectbox_locator)
            if timer_type != "Once":
                self.select_dropdown_by_value(
                    timer_subtype, *self._timer_subtype_selectbox_locator)
            if self.will_change_time_zone(time_zone):
                # set the starting hour to "1" to be able to check for element change later
                self.select_dropdown_by_value("1", *self._start_hour_selectbox_locator)
                # select timezone by substring in text
                self.select_dropdown_substring(time_zone, *self._time_zone_selectbox_locator)
                # wait for timezone javascript to reset the starting date and time
                wait_for(self.is_starting_date_reset, num_sec=3)
                # now we can continue filling out the date and time
            self.selenium.find_element(*self._start_date_field_locator)._parent.execute_script(
                "$j('#miq_date_1').attr('value', '%s')" % start_date)
            self.select_dropdown_by_value(start_hour, *self._start_hour_selectbox_locator)
            self.select_dropdown_by_value(start_min, *self._start_min_selectbox_locator)
            self._wait_for_results_refresh()

        def fill_data_analysis_or_compliance_check(self,
                                                   name="test_analysis_or_compliance_check",
                                                   description="test_description",
                                                   active=True,
                                                   action_type="vm",
                                                   filter_type="all",
                                                   filter_value="",
                                                   timer_type="Monthly",
                                                   timer_subtype="6",
                                                   time_zone="UTC",
                                                   start_date="4/5/2063",
                                                   start_hour="1",
                                                   start_min="45"):
            self.fill_data(
                name=name,
                description=description,
                active=active,
                action_type=action_type,
                filter_type=filter_type,
                filter_value=filter_value,
                timer_type=timer_type,
                timer_subtype=timer_subtype,
                time_zone=time_zone,
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min)

        def fill_data_smb_db_backup(self,
                                    name="smb_db_backup_test",
                                    description="test_description",
                                    active=True,
                                    uri="samba-fqdn-or-ip",
                                    user_id="smb_user_id",
                                    password="smb_pass",
                                    verify="smb_pass",
                                    timer_type="Once",
                                    timer_subtype="",
                                    time_zone="UTC",
                                    start_date="4/5/2063",
                                    start_hour="1",
                                    start_min="45"):
            self.fill_data(
                name=name,
                description=description,
                active=active,
                action_type="db_backup",
                log_type="Samba",
                uri=uri,
                user_id=user_id,
                password=password,
                verify=verify,
                timer_type=timer_type,
                timer_subtype=timer_subtype,
                time_zone=time_zone,
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min)

        def fill_data_nfs_db_backup(self,
                                    name="nfs_db_backup_test",
                                    description="test_description",
                                    active=True,
                                    uri="nfs-fqdn-or-ip",
                                    timer_type="Once",
                                    timer_subtype="",
                                    time_zone="UTC",
                                    start_date="4/5/2063",
                                    start_hour="1",
                                    start_min="45"):
            self.fill_data(
                name=name,
                description=description,
                active=active,
                action_type="db_backup",
                log_type="Network File System",
                uri=uri,
                timer_type=timer_type,
                timer_subtype="",
                time_zone=time_zone,
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min)

        def click_on_add(self):
            self._wait_for_visible_element(*self._add_button_locator)
            self.add_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings(self.testsetup)

        def click_on_cancel(self):
            self._wait_for_visible_element(*self._cancel_button_locator)
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings(self.testsetup)

        def click_on_validate(self):
            self._wait_for_visible_element(*self._smb_validate_button_locator)
            self.validate_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings.NewSchedule(self.testsetup)

    class EditSchedule(NewSchedule):
        _save_button_locator = (By.CSS_SELECTOR,
            "ul#form_buttons > li > img[title='Save Changes']")
        _reset_button_locator = (By.CSS_SELECTOR,
            "ul#form_buttons > li > img[title='Reset Changes']")

        @property
        def save_button(self):
            return self.selenium.find_element(*self._save_button_locator)

        @property
        def reset_button(self):
            return self.selenium.find_element(*self._reset_button_locator)

        def click_on_save(self):
            self._wait_for_visible_element(*self._save_button_locator)
            self.save_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings(self.testsetup)

        def click_on_reset(self):
            self._wait_for_visible_element(*self._reset_button_locator)
            self.reset_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings.EditSchedule(self.testsetup)

        def click_on_cancel(self):
            ''' Overrides click_on_cancel() from NewSchedule '''
            self._wait_for_visible_element(*self._cancel_button_locator)
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings.ShowSchedule(self.testsetup)

        def click_on_validate(self):
            ''' Overrides click_on_validate() from NewSchedule '''
            self._wait_for_visible_element(*self._smb_validate_button_locator)
            self.validate_button.click()
            self._wait_for_results_refresh()
            return ScheduleSettings.EditSchedule(self.testsetup)

    class ShowSchedule(ScheduleSettingsCommon):
        _name_prefix = "Settings Schedule"
        _name_top_label_locator = (By.XPATH,
            "//div[@class='dhtmlxInfoBarLabel' and contains(text(), '%s')]" % _name_prefix)

        _description_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(1) > td:nth-child(2)")
        _active_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(2) > td:nth-child(2)")
        _action_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(3) > td:nth-child(2)")
        _run_at_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(4) > td:nth-child(2)")
        _last_run_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(5) > td:nth-child(2)")
        _next_run_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(6) > td:nth-child(2)")
        _zone_text_locator = (By.CSS_SELECTOR,
            ".style1 tr:nth-child(7) > td:nth-child(2)")

        _edit_button_locator = (By.CSS_SELECTOR,
            "tr[title='Edit this Schedule'] > td.td_btn_txt > div")
        _delete_button_locator = (By.CSS_SELECTOR,
            "tr[title='Delete this Schedule from the Database'] > td.td_btn_txt > div")

        @property
        def name(self):
            text = self.selenium.find_element(*self._name_top_label_locator).text
            return re.match(r'%s \"(.*)\"' % self._name_prefix, text, re.IGNORECASE).group(1)

        @property
        def description(self):
            return self.selenium.find_element(*self._description_text_locator).text

        @property
        def active(self):
            return self.selenium.find_element(*self._active_text_locator).text

        @property
        def is_active(self):
            return self.active == "true"

        @property
        def action(self):
            return self.selenium.find_element(*self._action_text_locator).text

        @property
        def run_at(self):
            return self.selenium.find_element(*self._run_at_text_locator).text

        @property
        def last_run_time(self):
            return self.selenium.find_element(*self._last_run_text_locator).text

        @property
        def next_run_time(self):
            return self.selenium.find_element(*self._next_run_text_locator).text

        @property
        def zone(self):
            return self.selenium.find_element(*self._zone_text_locator).text

        @property
        def edit_button(self):
            return self.selenium.find_element(*self._edit_button_locator)

        @property
        def delete_button(self):
            return self.selenium.find_element(*self._delete_button_locator)

        def click_on_edit(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                .click(self.edit_button).perform()
            self._wait_for_results_refresh()
            return ScheduleSettings.EditSchedule(self.testsetup)

        def click_on_delete(self, cancel=False):
            ActionChains(self.selenium).click(self.configuration_button)\
                .click(self.delete_button).perform()
            self.handle_popup(cancel)
            self._wait_for_results_refresh()
            return ScheduleSettings(self.testsetup)
