# -*- cocing: utf-8 -*-
from cfme.web_ui import toolbar as tb, Region
from cfme.web_ui.tables import Table
from functools import partial

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')

list_tbl = Table.create("//div[@id='list_grid']//table", {'checkbox'})
details_page = Region(infoblock_type='detail')
