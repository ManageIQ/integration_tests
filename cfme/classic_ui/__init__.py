# -*- coding: utf-8 -*-
from pomoc.library import Input, Link
from pomoc.patternfly import Button
from pomoc.navigator import Navigator
from pomoc.objects import View

from .widgets import TwoLevelMenuItem


class CFMEView(View):
    class menu(View):
        dashboard = TwoLevelMenuItem('Cloud Intel', 'Dashboard')
        reports = TwoLevelMenuItem('Cloud Intel', 'Reports')
        chargeback = TwoLevelMenuItem('Cloud Intel', 'Chargeback')
        timelines = TwoLevelMenuItem('Cloud Intel', 'Timelines')
        rss = TwoLevelMenuItem('Cloud Intel', 'RSS')

        @Navigator.transition_to('Dashboard')
        def go_to_dashboard(self):
            self.dashboard.click()

        @Navigator.transition_to('Reports')
        def go_to_reports(self):
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
    reset_button = Button(title='Reset Dashboard Widgets to the defaults')

    def on_view(self):
        return self.reset_button.is_displayed


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
