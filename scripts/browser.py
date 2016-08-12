#!/usr/bin/env python2
from __future__ import unicode_literals
from IPython import embed

import cfme.fixtures.pytest_selenium as sel

sel.force_navigate('dashboard')
embed()
