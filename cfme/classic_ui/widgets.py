# -*- coding: utf-8 -*-
from xml.sax.saxutils import quoteattr

from pomoc.objects import Widget


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


class ContentTitle(Widget):
    def __init__(self, parent, title):
        super(ContentTitle, self).__init__(parent)
        self.title = title

    def __locator__(self):
        return '//div[@id="main-content"]//h1[normalize-space(.)={}]'.format(quoteattr(self.title))
