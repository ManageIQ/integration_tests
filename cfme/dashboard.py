"""Provides functions to manipulate the dashboard landing page.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the dashboard page
"""
import re

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Region, Table, tabstrip, toolbar
from utils import deferred_verpick, version
from utils.timeutil import parsetime
from utils.pretty import Pretty
from utils.wait import wait_for

page = Region(
    title="Dashboard",
    locators={
        'reset_widgets_button': toolbar.root_loc('Reset Dashboard Widgets'),
        'csrf_token': "//meta[@name='csrf-token']",
        'user_dropdown': {
            version.LOWEST: '//div[@id="page_header_div"]//li[contains(@class, "dropdown")]',
            '5.4': '//nav//ul[contains(@class, "navbar-utility")]'
                   '/li[contains(@class, "dropdown")]/a'
        }
    },
    identifying_loc='reset_widgets_button')


def reset_widgets(cancel=False):
    """Resets the widgets on the dashboard page.

    Args:
        cancel: Set whether to accept the popup confirmation box. Defaults to ``False``.
    """
    sel.click(page.reset_widgets_button, wait_ajax=False)
    sel.handle_alert(cancel)


def dashboards():
    """Returns a generator that iterates through the available dashboards"""
    sel.force_navigate("dashboard")
    # We have to click any other of the tabs (glitch)
    # Otherwise the first one is not displayed (O_O)
    tabstrip.select_tab(tabstrip.get_all_tabs()[-1])
    for dashboard_name in tabstrip.get_all_tabs():
        tabstrip.select_tab(dashboard_name)
        yield dashboard_name


class Widget(Pretty):
    _name = deferred_verpick({
        version.LOWEST: "//div[@id='{}']//span[contains(@class, 'modtitle_text')]",
        "5.5": "//div[@id='{}']//h3"})
    _remove = "//div[@id='{}']//a[@title='Remove from Dashboard']"
    _minimize = "//div[@id='{}']//a[@title='Minimize']"
    _restore = "//div[@id='{}']//a[@title='Restore']"
    _footer = "//div[@id='{}']//div[@class='modboxfooter' or contains(@class, 'panel-footer')]"
    _zoom = "//div[@id='{}']//a[@title='Zoom in on this chart']"
    _zoomed_name = deferred_verpick({
        version.LOWEST: "//div[@id='lightbox_div']//span[contains(@class, 'modtitle_text')]",
        "5.5": "//div[@id='lightbox_div']//h3"})
    _zoomed_close = deferred_verpick({
        version.LOWEST: "//div[@id='lightbox_div']//a[@title='Close']",
        "5.5": "//div[@id='lightbox_div']//a[@title='Close']/i"})
    _all = "//div[@id='modules']//div[contains(@id, 'w_')]"
    _content = deferred_verpick({
        version.LOWEST: "//div[@id='{}']//div[contains(@class, 'modboxin')]",
        "5.5": "//div[@id='{}']//div[contains(@class,'panel-body')]/div[contains(@id, 'box')]"})
    _content_type_54 = "//div[@id='{}']//div[contains(@class, 'modboxin')]/../h2/a[1]"

    # 5.5+ updated
    _menu_opener = "//div[@id='{}']//a[contains(@class, 'dropdown-toggle')]/i"
    _menu_container = "//div[@id='{}']//ul[contains(@class, 'dropdown-menu')]"
    _menu_minmax = _menu_container + "/li/a[contains(@id, 'minmax')]"
    _menu_remove = _menu_container + "/li/a[contains(@id, 'close')]"
    _menu_zoom = _menu_container + "/li/a[contains(@id, 'zoom')]"

    pretty_attrs = ['_div_id']

    def __init__(self, div_id):
        self._div_id = div_id

    @property
    def newer_version(self):
        return version.current_version() >= "5.5"

    @property
    def name(self):
        return sel.text(self._name.format(self._div_id)).encode("utf-8")

    @property
    def content_type(self):
        if version.current_version() < "5.4" or self.newer_version:
            return sel.get_attribute(self._content.format(self._div_id), "class").rsplit(" ", 1)[-1]
        else:
            return sel.get_attribute(self._content_type_54.format(self._div_id), "class").strip()

    @property
    def content(self):
        if self.content_type in {"rss_widget", "rssbox"}:
            return RSSWidgetContent(self._div_id)
        elif self.content_type in {"report_widget", "reportbox"}:
            return ReportWidgetContent(self._div_id)
        else:
            return BaseWidgetContent(self._div_id)

    @property
    def footer(self):
        cleaned = [
            x.strip()
            for x
            in sel.text(self._footer.format(self._div_id)).encode("utf-8").strip().split("|")
        ]
        result = {}
        for item in cleaned:
            name, time = item.split(" ", 1)
            time = time.strip()
            if time.lower() == "never":
                result[name.strip().lower()] = None
            else:
                result[name.strip().lower()] = parsetime.from_american_minutes(time.strip())
        return result

    @property
    def time_updated(self):
        return self.footer["updated"]

    @property
    def time_next(self):
        return self.footer["next"]

    @property
    def is_minimized(self):
        self.close_zoom()
        if not self.newer_version:
            return not sel.is_displayed(self._minimize.format(self._div_id))
        else:
            return not sel.is_displayed(self._content.format(self._div_id))

    @property
    def can_zoom(self):
        """Can this Widget be zoomed?"""
        self.close_zoom()
        if not self.newer_version:
            return sel.is_displayed(self._zoom.format(self._div_id))
        else:
            self.open_dropdown_menu()
            zoomable = sel.is_displayed(self._menu_zoom.format(self._div_id))
            self.close_dropdown_menu()
            return zoomable

    def _click_menu_button_by_loc(self, loc):
        self.close_zoom()
        try:
            self.open_dropdown_menu()
            sel.click(loc.format(self._div_id))
        finally:
            self.close_dropdown_menu()

    def remove(self, cancel=False):
        """Remove this Widget."""
        self.close_zoom()
        if not self.newer_version:
            sel.click(self._remove.format(self._div_id), wait_ajax=False)  # alert
            sel.handle_alert(cancel)
        else:
            self._click_menu_button_by_loc(self._menu_remove)

    def minimize(self):
        """Minimize this Widget."""
        self.close_zoom()
        if not self.is_minimized:
            if not self.newer_version:
                sel.click(self._minimize.format(self._div_id))
            else:
                self._click_menu_button_by_loc(self._menu_minmax)

    def restore(self):
        """Return the Widget back from minimalization."""
        self.close_zoom()
        if self.is_minimized:
            if not self.newer_version:
                sel.click(self._restore.format(self._div_id))
            else:
                self._click_menu_button_by_loc(self._menu_minmax)

    def zoom(self):
        """Zoom this Widget."""
        self.close_zoom()
        if not self.is_zoomed():
            if not self.newer_version:
                sel.click(self._zoom.format(self._div_id))
            else:
                self._click_menu_button_by_loc(self._menu_zoom)

    @classmethod
    def is_zoomed(cls):
        return sel.is_displayed(cls._zoomed_name)

    @classmethod
    def get_zoomed_name(cls):
        return sel.text(cls._zoomed_name).encode("utf-8").strip()

    @classmethod
    def close_zoom(cls):
        if cls.is_zoomed():
            sel.click(cls._zoomed_close)
            # Here no ajax, so we have to check it manually
            wait_for(lambda: not cls.is_zoomed(), delay=0.1, num_sec=5, message="cancel zoom")

    @classmethod
    def all(cls):
        """Returns objects with all Widgets currently present."""
        result = []
        for el in sel.elements(cls._all):
            result.append(cls(sel.get_attribute(el, "id")))
        return result

    @classmethod
    def by_name(cls, name):
        """Returns Widget with specified name."""
        for widget in cls.all():
            if widget.name == name:
                return widget
        else:
            raise NameError("Could not find widget with name {} on current dashboard!".format(name))

    @classmethod
    def by_type(cls, content_type):
        """Returns Widget with specified content_type."""
        return filter(lambda w: w.content_type == content_type, cls.all())

    # 5.5+ specific methods
    @property
    def is_dropdown_menu_opened(self):
        return sel.is_displayed(self._menu_container.format(self._div_id))

    def open_dropdown_menu(self):
        if not sel.is_displayed(self._menu_opener.format(self._div_id)):
            return  # Not a 5.5+
        self.close_dropdown_menu()
        sel.click(self._menu_opener.format(self._div_id))
        wait_for(
            lambda: self.is_dropdown_menu_opened,
            num_sec=10, delay=0.2, message="widget dropdown menu opend")

    def close_dropdown_menu(self):
        if not sel.is_displayed(self._menu_opener.format(self._div_id)):
            return  # Not a 5.5+
        if self.is_dropdown_menu_opened:
            sel.click("//a[contains(@class, 'navbar-brand')]/img")
            wait_for(
                lambda: not self.is_dropdown_menu_opened,
                num_sec=10, delay=0.2, message="widget dropdown menu closed")


class BaseWidgetContent(Pretty):
    pretty_attrs = ['widget_box_id']

    def __init__(self, widget_box_id):
        self.root = lambda: sel.element(
            "//div[@id='{}']//div[contains(@class, 'modboxin')]".format(widget_box_id))

    @property
    def data(self):
        return sel.element("./div[contains(@id, 'dd_')]", root=self.root)


class RSSWidgetContent(BaseWidgetContent):
    @property
    def data(self):
        result = []
        for row in sel.elements("./div/table/tbody/tr/td", root=self.root):
            # Regular expressions? Boring.
            desc, date = sel.text(row).encode("utf-8").strip().rsplit("\n", 1)
            date = date.split(":", 1)[-1].strip()
            date = parsetime.from_iso_with_utc(date)
            url_source = sel.element("./..", root=row).get_attribute("onclick")
            getter_script = re.sub(r"^window.location\s*=\s*([^;]+;)", "return \\1", url_source)
            try:
                url = sel.execute_script(getter_script)
            except sel.WebDriverException:
                url = None
            result.append((desc, date, url))
        return result


class ReportWidgetContent(BaseWidgetContent):
    @property
    def data(self):
        return Table(lambda: sel.element("./div/table[thead]", root=self.root))


def get_csrf_token():
    """Retuns current CSRF token.

    Returns: Current  CSRF token.
    """
    return sel.get_attribute(page.csrf_token, "content")


def set_csrf_token(csrf_token):
    """Changing the CSRF Token on the fly via the DOM by iterating over the meta tags

    Args:
        csrf_token: Token to set as the CSRF token.
    """
    return sel.set_attribute(page.csrf_token, "content", csrf_token)
