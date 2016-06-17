from . import Endpoint


class DBEndpoint(Endpoint):
    """DB endpoint"""

    def __init__(self, name, impl, owner):
        """DB Endpoint"""
        super(DBEndpoint, self).__init__(name=name, impl=impl, owner=owner)

    # ** I admit it, this is a hack right now. The DB session should be in this file. Again
    # ** this is what these endpoints are for, defining the place where sessions and their
    # ** interactions live.
    # ** This is why we need owner in here currently. Can it go in the future? perhaps.
    @property
    def db(self):
        return self.owner.db
