#/usr/bin/env python

from pages.base import Base

class Infrastructure(Base):
    class ManagementSystems(Base):
        _page_title = 'ManageIQ EVM: Management Systems'

    class PXE(Base):
        _page_title = 'ManageIQ EVM: PXE'

