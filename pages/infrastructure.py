# -*- coding: utf-8 -*-

from pages.base import Base

class Infrastructure(Base):
    class ManagementSystems(Base):
        _page_title = 'CloudForms Management Engine: Management Systems'

        @property
        def quadicons(self):
            from pages.regions.quadicons import Quadicons
            return Quadicons(self.testsetup).quadicons
        
        @property
        def paginator(self):
            from pages.regions.paginator import Paginator
            return Paginator(self.testsetup)

    class PXE(Base):
        _page_title = 'CloudForms Management Engine: PXE'
