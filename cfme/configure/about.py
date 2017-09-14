# -*- coding: utf-8 -*-
from widgetastic.widget import View
from widgetastic_patternfly import AboutModal

from cfme.exceptions import ElementOrBlockNotFound
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to

# MIQ/CFME about field names
VERSION = 'Version'
SERVER = 'Server Name'
USER = 'User Name'
ROLE = 'User Role'
BROWSER = 'Browser'
BROWSER_VERSION = 'Browser Version'
BROWSER_OS = 'Browser OS'


class AboutView(View):
    """
    The view for the about modal
    """
    @property
    def is_displayed(self):
        return self.modal.is_open

    modal = AboutModal(id='aboutModal')


def get_detail(field):
    """
    Open the about modal and fetch the value for one of the fields
    'title' and 'trademark' fields are allowed and get the header/footer values
    Raises ElementOrBlockNotFound if the field isn't in the about modal
    :param field: string label for the detail field
    :return: string value from the requested field
    """
    view = navigate_to(current_appliance().server, 'About')

    try:
        if field.lower() in ['title', 'trademark']:
            return getattr(view.modal, field.lower())
        else:
            return view.modal.items()[field]
    except KeyError:
        raise ElementOrBlockNotFound('No field named {} found in "About" modal.'.format(field))
    finally:
        # close since its a blocking modal and will break further navigation
        view.modal.close()
