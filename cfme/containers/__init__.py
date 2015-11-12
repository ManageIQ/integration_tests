from cfme.web_ui import SplitTable, toolbar as tb
from functools import partial

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')

list_tbl = SplitTable(
    header_data=("//div[@id='list_grid']/div[@class='xhdr']/table/tbody", 1),
    body_data=("//div[@id='list_grid']/div[@class='objbox']/table/tbody", 1),
)
