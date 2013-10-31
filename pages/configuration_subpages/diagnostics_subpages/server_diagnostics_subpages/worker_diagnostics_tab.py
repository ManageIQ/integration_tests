from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.taskbar.taskbar import TaskbarMixin
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait


class Worker(object):
    """ Worker informations

    This class encapsulates all informations from the worker table.
    Also allows restarting of the worker.
    """

    def __init__(self, cells, parent_tab):
        self.parent = parent_tab
        self.name = cells[1].text
        self.status = cells[2].text
        self.pid = int(cells[3].text)
        self.spid = cells[4].text
        self.uri = cells[5].text
        self.started = cells[6].text
        self.last_heartbeat = cells[7].text
        self.memory_usage = cells[8].text
        self.memory_size = cells[9].text
        self.cpu_percent = cells[10].text
        self.cpu_time = cells[11].text

    def restart(self):
        """ Restart this worker

        It calls the parent tab's restart method.
        This object is then invalid because the worker is relaunched with new PID.
        """
        self.parent.restart_worker(self.pid)


class WorkerDiagnosticsTab(Base, TaskbarMixin):
    """ Configure
        Configuration
        Diagnostics accordion
        Workers

    Querying informations about running workers and restarting of them.
    """
    _page_title = 'CloudForms Management Engine: Configuration'
    _configuration_button_locator = (By.CSS_SELECTOR,
            "div.dhx_toolbar_btn[title='Configuration']")
    _restart_worker_locator = (By.CSS_SELECTOR,
            "tr[title='Select a worker to restart']\
                    >td.td_btn_txt>div.btn_sel_text")
    _refresh_locator = (By.XPATH, "//*[@id='miq_alone']/img")
    _table_rows_locator = (By.CSS_SELECTOR, "table.style3 > tbody > tr")
    _positions = {"Name": 2,
                  "Status": 3,
                  "PID": 4,
                  "SPID": 5,
                  "URI": 6,
                  "Started": 7,
                  "Last Heartbeat": 8,
                  "Memory Usage": 9,
                  "Memory Size": 10,
                  "CPU Percent": 11,
                  "CPU Time": 12
                  }

    @property
    def restart_button(self):
        """ Restart button.

        Used for restarting the worker.
        Can be used only when some worker is selected.
        """
        return self.selenium.find_element(*self._restart_worker_locator)

    @property
    def refresh_button(self):
        """ Refresh button.

        Used for refreshing the page.
        Can shuffle the order.
        """
        return self.selenium.find_element(*self._refresh_locator)

    def find_workers(self, key, by="Name"):
        """ Finds workers.

        Finds workers by any of the column parameters.

        Returns Worker objects with informations about each worker found
        """
        assert by in self._positions.keys(), "find_workers()'s by parameter is incorrect!"
        table_rows = self.selenium.find_elements(*self._table_rows_locator)
        result = []
        for row in table_rows:
            # This is ugly but the XPath did silly things
            cells = row.find_elements(By.XPATH, "./*")
            assert len(cells) == 12, "Incorrect number of cells in row"
            if cells[self._positions[by] - 1].text == key:
                result.append(Worker(cells, self))
        return result

    def wait_for(self, fun, time=15):
        """ Wrapper for WebDriverWait

        """
        return WebDriverWait(self.selenium, time).until(fun)

    def select_worker(self, pid):
        """ Worker selection.

        Clicks on the worker row and waits until it's selected (its row is .row3)
        """
        locator = "//table[@class='style3']/tbody/tr/td[%d][@title='%s']" % \
            (self._positions["PID"], str(pid))
        worker = self.selenium.find_element(By.XPATH, locator)
        assert worker, "No worker with PID %d found" % pid
        worker.click()
        locator_selected = "//table[@class='style3']/tbody/tr[@class='row3']/td[%d][@title='%s']" %\
            (self._positions["PID"], str(pid))
        self.wait_for(lambda s: s.find_element_by_xpath(locator_selected))

    def restart_selected_worker(self, click_cancel=False):
        """ Worker restart.

        This clicks on the Configuration button and then on Restart button in the menu.
        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.restart_button)\
            .perform()
        self.handle_popup(click_cancel)
        self._wait_for_results_refresh()

    def restart_worker(self, pid, click_cancel=False):
        """ Restart worker via PID.

        This combines clicking on a worker row and then clicking the restart button
        """
        self.select_worker(pid)
        self.restart_selected_worker(click_cancel)

    def restart_workers_by_name(self, name):
        """ restart workers from same group.

        There are workers having the same names so this can restart each of them precisely.
        This can be used as a test whether this page's code works properly as it uses all
        functions from it.
        """
        for worker in self.find_workers(name, by="Name"):
            worker.restart()
            assert "restart initiated successfully" in self.flash.message
            self.click_on_refresh()     # This can shuffle the order of the workers,
                                        # so it can be used as a sort of "testing" whether
                                        # the code handles it well ...

    def click_on_refresh(self):
        """ Refreshes the page

        Clicks on a refresh button and waits until refresh is finished.
        """
        self.refresh_button.click()
        self._wait_for_results_refresh()
