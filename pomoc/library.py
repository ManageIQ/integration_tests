# -*- coding: utf-8 -*-
from xml.sax.saxutils import quoteattr

from .objects import Widget


class Clickable(object):
    def click(self, **kwargs):
        self.browser.click(self, **kwargs)


class ByTextOrAttr(Widget):
    ALLOWED_ATTRS = {'title', 'alt'}

    def __init__(self, parent, *text, **by_attr):
        super(ByTextOrAttr, self).__init__(parent)
        if text:
            if len(text) > 1:
                raise TypeError('For text based buttons you can only pass one param')
            else:
                self.text = text[0]
        else:
            self.text = None
            self.attr = None
            for attr, value in by_attr.iteritems():
                if attr not in self.ALLOWED_ATTRS:
                    raise NameError('Attribute {} is not allowed for buttons'.format(attr))
                if self.attr:
                    raise ValueError('You are specifying multiple attributes to match')
                self.attr = (attr, value)


class Link(ByTextOrAttr, Clickable):
    def __locator__(self):
        if self.text is not None:
            return '//a[normalize-space(.)={}]'.format(quoteattr(self.text))
        else:
            return '//a[@{}={}]'.format(self.attr[0], quoteattr(self.attr[1]))


class Input(Widget, Clickable):
    def __init__(self, parent, id):
        super(Input, self).__init__(parent)
        self.id = id

    def fill(self, text):
        self.browser.send_keys(text, self)

    def __locator__(self):
        return 'input#{}'.format(self.id)
