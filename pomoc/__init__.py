# -*- coding: utf-8 -*-

from pomoc.navigator import Navigator
from pomoc.objects import View


##################
# Some test data
#

class Test1(View):
    def on_view(self):
        pass


class Test2(View):
    def on_view(self):
        pass


class MenuMixin(object):
    @Navigator.transition_to(Test1, Test2)
    def go_to_test(self, a, b):
        pass


class InMenuA(View, MenuMixin):
    pass


class InMenuB(View, MenuMixin):
    pass


class InMenuC(View, MenuMixin):
    pass


class Entry(View):
    def on_load(self):
        self.browser.get('asdf')

    @Navigator.transition_to(InMenuA)
    def go_to_menu_a(self):
        pass

    @Navigator.transition_to(InMenuB)
    def go_to_menu_b(self):
        pass

    @Navigator.transition_to(InMenuC)
    def go_to_menu_c(self):
        pass
