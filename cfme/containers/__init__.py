# deleted list_tbl definition to prevent caching
from __future__ import unicode_literals
from cfme.web_ui import toolbar as tb, Region
from functools import partial

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')

details_page = Region(infoblock_type='detail')
