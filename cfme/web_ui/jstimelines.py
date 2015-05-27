"""
A Timelines object represents the Timelines widget in CFME using JS integration
instead of relying on WebElements

Args:
    loc: A locator for the Timelines element, usually the div with
        id miq_timeline.
"""
import os
import re

import cfme.fixtures.pytest_selenium as sel
from utils.pretty import Pretty


class Object(Pretty):
    """
    A generic timelines object.

    Args:
        element: A WebElement for the event.
    """
    pretty_attrs = ['element']

    def __init__(self, element):
        self.element = element

    def locate(self):
        return self.element


class Event(Object):
    """
    An event object.
    """
    window_loc = '//div[@class="timeline-event-bubble-title"]/../..'
    close_button = "{}/div[contains(@style, 'close-button')]".format(window_loc)
    data_block = '{}//div[@class="timeline-event-bubble-body"]'.format(window_loc)

    @property
    def image(self):
        """ Returns the image name of an event. """
        icon = self.element['_icon']
        return os.path.split(icon)[1]

    def block_info(self):
        """ Attempts to return a dict with the information from the popup. """
        data = {}

        elem = self.element['_description'].replace("<br />", "\n")
        elem = elem.replace("<br/>", "\n")
        elem = re.sub('<.*?>', '', elem)

        text_elements = elem.split("\n")
        for line in text_elements:
            line += " "
            kv = line.split(": ")
            if len(kv) == 1:
                if ':' not in kv[0]:
                    data['title'] = kv[0].strip()
                else:
                    data[kv[0]] = None
            else:
                data[kv[0]] = kv[1].strip()
        return data


def _list_events():
    try:
        soutput = sel.execute_script('return tl._bands[0]._eventSource._events._events._a')
        return soutput
    except sel.WebDriverException:
        return []


def find_visible_events_for_vm(vm_name):
    """ Finds all events for a given vm.

    Args:
        vm_name: The vm name.
    """
    events = []
    for event in events():
        info = event.block_info()
        if info.get('title', None) == vm_name:
            events.append(event)
            return events


def events():
    """ A generator yielding all events. """
    for el in _list_events():
        yield Event(el)
