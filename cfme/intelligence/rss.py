# -*- coding: utf-8 -*-
from cfme import BaseLoggedInPage


class RSSView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Cloud Intel', 'RSS'])
