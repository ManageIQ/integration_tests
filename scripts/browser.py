#!/usr/bin/env python3
from IPython import embed

from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to

navigate_to(current_appliance.server, 'Dashboard')
embed()
