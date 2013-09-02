''' Created on July 25, 2013

@author: Shveta
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.list import ListRegion, ListItem


class OrderService(Base):
    '''Order catalog page'''
    _order_list_locator = (
         By.CSS_SELECTOR, 
         "div#list_grid > div.objbox > table > tbody")
          
    @property
    def order_catalog_list(self):
        '''Select item to order'''
        return ListRegion(self.testsetup, 
                self.get_element(*self._order_list_locator), 
                self.OrderListItem)
          
    class OrderListItem(ListItem):
        '''Order Item table'''
        _columns = ["icon", "name", "description"]
        
        def click(self):
            ''' Click '''
            self._item_data[1].click()


        @property
        def name(self):
            '''Name'''
            return self._item_data[2].text

        @property
        def description(self):
            '''Desc'''
            return self._item_data[3].text
    