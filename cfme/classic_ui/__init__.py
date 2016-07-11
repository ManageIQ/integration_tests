# -*- coding: utf-8 -*-
from pomoc.library import Input, Link
from pomoc.patternfly import Button
from pomoc.navigator import Navigator
from pomoc.objects import View

from .menu import TopMenu


class Login(View):
    username = Input('user_name')
    password = Input('user_password')
    login = Button('Login')
    update = Link('Update password')

    # Currently, the Menu will be separate views since this would have to lead to many many
    # possible targets ....
    @Navigator.transition_to(TopMenu)
    def login_user(self, user):
        self.username.fill(user.credential.principal)
        self.password.fill(user.credential.secret)
        self.login.click()

    def on_load(self):
        """Currently stuff is handled with ensure_browser_open() ..."""
