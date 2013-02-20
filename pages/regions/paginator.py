# -*- coding: utf-8 -*-

class Paginator(Page):

    #Numbering
    _page_number_locator = (By.CSS_SELECTOR, '#paging_div .num > a:nth-child(1)')
    _total_page_number_locator = (By.CSS_SELECTOR, '#paging_div .num > a:nth-child(2)')

    #Navigation
    _first_page_locator = (By.CSS_SELECTOR, "#paging_div * img[alt='First']")
    _prev_locator = (By.CSS_SELECTOR, "#paging_div * img[alt='Previous']")
    _next_locator = (By.CSS_SELECTOR, "#paging_div * img[alt='Next']")
    _last_page_locator = (By.CSS_SELECTOR, "#paging_div * img[alt='Last']")

    #Position
    _position_text_locator = (By.CSS_SELECTOR, '#paging_div .pos b:nth-child(1)')
    

    _updating_locator = (By.CSS_SELECTOR, "div.updating")

    def _wait_for_results_refresh(self):
        # On pages that do not have ajax refresh this wait will have no effect.
        WebDriverWait(self.selenium, self.timeout).until(lambda s: not self.is_element_present(*self._updating_locator))

    @property
    def page_number(self):
        return int(self.selenium.find_element(*self._page_number_locator).text)

    @property
    def total_page_number(self):
        return int(self.selenium.find_element(*self._total_page_number_locator).text)

    def click_first_page(self):
        self.selenium.find_element(*self._first_page_locator).click()
        self._wait_for_results_refresh()

    def click_prev_page(self):
        self.selenium.find_element(*self._prev_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_prev_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._prev_locator).get_attribute('class')

    @property
    def is_first_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._first_page_locator).get_attribute('class')

    def click_next_page(self):
        self.selenium.find_element(*self._next_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_next_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._next_locator).get_attribute('class')

    def click_last_page(self):
        self.selenium.find_element(*self._last_page_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_last_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._last_page_locator).get_attribute('class')

    @property
    def start_item(self):
        return int(self.selenium.find_element(*self._start_item_number_locator).text)

    @property
    def end_item(self):
        return int(self.selenium.find_element(*self._end_item_number_locator).text)

    @property
    def total_items(self):
        text = self.selenium.find_element(*self._total_item_number).text
        return int(self.selenium.find_element(*self._total_item_number).text)
