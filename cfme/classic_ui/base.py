# -*- coding: utf-8 -*-
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
