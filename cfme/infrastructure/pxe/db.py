from . import PXEServer
from utils.appliance import ViaDB


@PXEServer.exists.external_implementation_for(ViaDB)
def pxeserver_exists(self):
    """
    Checks if the PXE server already exists
    """
    return self.impl.db.session.query(
        self.impl.db["pxe_servers"]
    ).filter_by(
        name=self.name
    ).count() > 0
