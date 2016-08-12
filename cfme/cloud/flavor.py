""" Page functions for Flavor pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""

from __future__ import unicode_literals
from cfme.web_ui import Region, SplitTable


# Page specific locators
list_page = Region(
    locators={
        'flavor_table': SplitTable(header_data=('//div[@class="xhdr"]/table/tbody', 1),
            body_data=('//div[@class="objbox"]/table/tbody', 1))
    },
    title='Flavors')


details_page = Region(infoblock_type='detail')
