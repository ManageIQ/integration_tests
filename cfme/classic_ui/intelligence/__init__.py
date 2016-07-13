# -*- coding: utf-8 -*-
from pomoc.patternfly import Button

from cfme.classic_ui.base import CFMEView


class Dashboard(CFMEView):
    reset_button = Button(title='Reset Dashboard Widgets to the defaults')

    def on_view(self):
        return self.reset_button.is_displayed


class Reports(CFMEView):
    pass
