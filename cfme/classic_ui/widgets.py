# -*- coding: utf-8 -*-
from xml.sax.saxutils import quoteattr

from pomoc.objects import Widget
from pomoc.library import Clickable


class TopMenuItem(Widget, Clickable):
    def __init__(self, parent, name):
        super(TopMenuItem, self).__init__(parent)
        self.name = name

    @property
    def li_element(self):
        return self.browser.element('../..', parents=[self])

    @property
    def is_active(self):
        return 'active' in self.browser.classes(self.li_element)

    def __locator__(self):
        return '//ul[@id="maintab"]/li/a/span[normalize-space(.)={}]'.format(quoteattr(self.name))


class SecondMenuItem(Widget, Clickable):
    def __init__(self, parent, name):
        super(SecondMenuItem, self).__init__(parent)
        self.name = name

    @property
    def li_element(self):
        return self.browser.element('../..', parents=[self])

    @property
    def is_active(self):
        return 'active' in self.browser.classes(self.li_element)

    def __locator__(self):
        return '//ul[contains(@class, "list-group")]/li/a/span[normalize-space(.)={}]'.format(
            quoteattr(self.name))
