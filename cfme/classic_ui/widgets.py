# -*- coding: utf-8 -*-
from xml.sax.saxutils import quoteattr

from pomoc.objects import Widget


class TopMenuItem(Widget):
    def __init__(self, parent, name):
        super(TopMenuItem, self).__init__(parent)
        self.name = name

    def __locator__(self):
        return '//ul[@id="maintab"]/li/a/span[normalize-space(.)={}]'.format(quoteattr(self.name))


class SecondMenuItem(Widget):
    def __init__(self, parent, name):
        super(SecondMenuItem, self).__init__(parent)
        self.name = name

    def __locator__(self):
        return '//ul[contains(@class, "list-group")]/li/a/span[normalize-space(.)={}]'.format(
            quoteattr(self.name))
