# -*- coding: utf-8 -*-
from cfme.classic_ui.base import CFMEView
from cfme.classic_ui.widgets import ContentTitle


class InfrastructureProviders(CFMEView):
    title = ContentTitle('Infrastructure Providers')

    def on_view(self):
        return self.title.is_displayed
