from pages.page import Page
from pages.base import Base
import random
from pages.regions.checkboxtree import CheckboxTree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.regions.taggable import Taggable
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem


class OrderService(Base):
    _order_list_locator = (By.CSS_SELECTOR, "div#list_grid > div.objbox > table > tbody")
          
    @property
    def order_catalog_list(self):
        return ListRegion(self.testsetup,self.get_element(*self._order_list_locator),self.OrderListItem)
          
    class OrderListItem(ListItem):
        _columns = ["name", "description", "cost"]
        
        @property
        def name(self):
           print  len(self._item_data)
           return self._item_data[2].text

        @property
        def description(self):
           return self._item_data[3].text

        @property
        def cost(self):
           return self._item_data[4].text

    