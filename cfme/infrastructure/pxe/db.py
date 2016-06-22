from base import PXEBase
from utils.appliance import ViaDB


class PXEServerDB(PXEBase):
    # ** See the comments in the ui.py file for more information here.
    @PXEBase.exists.implemented_for(ViaDB)
    def existse(self):
        """
        Checks if the PXE server already exists
        """
        return self.impl.db.session.query(
            self.impl.db["pxe_servers"]
        ).filter_by(
            name=self.name
        ).count() > 0
