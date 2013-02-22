# -*- coding: utf-8 -*-

from pages.base import Base

class Services(Base):
    class VirtualMachines(Base):
        _page_title = 'ManageIQ EVM: Virtual Machines'
        
        @property
        def paginator(self):
            from pages.regions.paginator import Paginator
            return Paginator(self.testsetup)
        