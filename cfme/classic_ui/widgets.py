# -*- coding: utf-8 -*-
from xml.sax.saxutils import quoteattr

from pomoc.objects import Widget
from pomoc.library import Clickable


class TwoLevelMenuItem(Widget):
    LOC = (
        '//ul[@id="maintab"]/li/a/span[normalize-space(.)={}]/../../div/ul/li'
        '/a[./span[normalize-space(.)={}]]')

    def __init__(self, parent, toplevel, secondlevel):
        super(TwoLevelMenuItem, self).__init__(parent)
        self.toplevel = toplevel
        self.secondlevel = secondlevel

    def click(self):
        self.browser.execute_script(
            'document.location.href = arguments[0];',
            self.browser.get_attribute('href', self))

    def __locator__(self):
        return self.LOC.format(quoteattr(self.toplevel), quoteattr(self.secondlevel))


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


class SecondMenuHeader(Widget):
    def __init__(self, parent, title):
        super(SecondMenuHeader, self).__init__(parent)
        self.title = title

    def __locator__(self):
        return '//div[contains(@class, "nav-item-pf-header")]/span[normalize-space(.)={}]'.format(
            quoteattr(self.title))
