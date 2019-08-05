# -*- coding: utf-8 -*-
from widgetastic.widget import View
from widgetastic_patternfly import AboutModal

from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import navigate_to

# MIQ/CFME about field names
VERSION = 'Version'
SERVER = 'Server Name'
USER = 'User Name'
ROLE = 'User Role'
BROWSER = 'Browser'
BROWSER_VERSION = 'Browser Version'
BROWSER_OS = 'Browser OS'
ZONE = "Zone"
REGION = "Region"


class MIQAboutModal(AboutModal):
    """Override some locators that MIQ mangles"""
    CLOSE_LOC = './/div[@class="modal-header"]/button[@class="close"]'


class AboutView(View):
    """
    The view for the about modal
    """
    @property
    def is_displayed(self):
        return self.modal.is_open

    modal = MIQAboutModal()  # 5.10 has id, 5.11 does not, wt.pf doesn't need it.


def get_detail(field, server):
    """
    Open the about modal and fetch the value for one of the fields
    'title' and 'trademark' fields are allowed and get the header/footer values
    Raises ItemNotFound if the field isn't in the about modal
    :param field: string label for the detail field
    :return: string value from the requested field
    """

    view = navigate_to(server, 'About')

    try:
        if field.lower() in ['title', 'trademark']:
            return getattr(view.modal, field.lower())
        else:
            # this is AboutModal.items function, TODO rename
            return view.modal.items()[field]
    except (KeyError, AttributeError):
        raise ItemNotFound('No field named {} found in "About" modal.'.format(field))
    finally:
        # close since its a blocking modal and will break further navigation
        view.modal.close()
