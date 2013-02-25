# -*- coding: utf-8 -*-

from pages.base import Base
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem

class Services(Base):
    class VirtualMachines(Base):
        _page_title = 'ManageIQ EVM: Virtual Machines'
        
        @property        
        def quadicons(self):
            return Quadicons(self.testsetup,Services.VirtualMachines.VirtualMachineQuadIconItem).quadicons
        
        @property
        def paginator(self):
            from pages.regions.paginator import Paginator
            return Paginator(self.testsetup)
        
        class VirtualMachineQuadIconItem(QuadiconItem):
            @property
            def snapshots(self):
                return self._root_element.find_element(*self._quad_br_locator).text