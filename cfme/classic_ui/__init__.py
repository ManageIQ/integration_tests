# -*- coding: utf-8 -*-
from pomoc.library import Input, Link
from pomoc.patternfly import Button
from pomoc.navigator import Navigator
from pomoc.objects import View
from smartloc import Locator

from .widgets import TopMenuItem, SecondMenuItem, SecondMenuHeader


class CFMEView(View):
    class menu(View):
        class intelligence(View):
            brand = Locator('//img[@alt="ManageIQ"]')
            topmenuitem = TopMenuItem('Cloud Intel')
            header = SecondMenuHeader('Cloud Intel')
            dashboard = SecondMenuItem('Dashboard')
            reports = SecondMenuItem('Reports')
            chargeback = SecondMenuItem('Chargeback')
            timelines = SecondMenuItem('Timelines')
            rss = SecondMenuItem('RSS')

            @Navigator.transition_to('Dashboard')
            def go_to_dashboard(self):
                self.topmenuitem.click()
                self.browser.move_to_element(self.brand)
                self.topmenuitem.move_to_element()
                self.header.wait_displayed()
                self.dashboard.click()

            @Navigator.transition_to('Reports')
            def go_to_reports(self):
                self.topmenuitem.click()
                self.browser.move_to_element(self.brand)
                self.topmenuitem.move_to_element()
                self.header.wait_displayed()
                self.reports.click()
        # insights = TopMenuItem('Red Hat Insights')
        # services = TopMenuItem('Services')
        # compute = TopMenuItem('Compute')
        # configuration = TopMenuItem('Configuration')
        # networks = TopMenuItem('Networks')
        # control = TopMenuItem('Control')
        # automate = TopMenuItem('Automate')
        # optimize = TopMenuItem('Optimize')
        # settings = TopMenuItem('Settings')


class Dashboard(CFMEView):
    pass


class Reports(CFMEView):
    pass


class Login(View):
    username = Input('user_name')
    password = Input('user_password')
    login = Button('Login')
    update = Link('Update password')

    # Currently, the Menu will be separate views since this would have to lead to many many
    # possible targets ....
    @Navigator.transition_to(Dashboard)
    def login_user(self, user):
        self.username.fill(user.credential.principal)
        self.password.fill(user.credential.secret)
        self.login.click()

    def on_load(self):
        """Currently stuff is handled with ensure_browser_open() ..."""
