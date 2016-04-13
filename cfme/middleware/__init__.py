from cfme.web_ui import CheckboxTable, toolbar as tb
from functools import partial

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
