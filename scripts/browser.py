#!/usr/bin/env python2
from IPython import embed

from cfme.base import Server
from cfme.utils.appliance.implementations.ui import navigate_to

navigate_to(Server, 'Dashboard')
embed()
