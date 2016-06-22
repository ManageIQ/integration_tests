from . import Endpoint


class DBEndpoint(Endpoint):
    """DB endpoint"""

    def __init__(self, name, impl, owner):
        """DB Endpoint"""
        super(DBEndpoint, self).__init__(name=name, impl=impl, owner=owner)

    @property
    def db(self):
        return self.owner.db
