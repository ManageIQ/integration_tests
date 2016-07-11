# -*- coding: utf-8 -*-
from xml.sax.saxutils import quoteattr

from pomoc.library import ByTextOrAttr, Clickable


class Button(ByTextOrAttr, Clickable):
    ALLOWED_ATTRS = {'title', 'alt'}

    def __init__(self, parent, *text, **by_attr):
        super(Button, self).__init__(parent)
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

    def __locator__(self):
        if self.text is not None:
            return (
                '//a[contains(@class, "btn") and normalize-space(.)={}]'.format(
                    quoteattr(self.text)))
        else:
            return (
                '//a[contains(@class, "btn") and @{}={}]'.format(
                    self.attr[0], quoteattr(self.attr[1])))
