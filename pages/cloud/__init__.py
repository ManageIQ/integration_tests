from pages.base import Base
from pages.cloud.availability_zones import AvailabilityZones
from pages.cloud.providers import Providers
from pages.cloud.instances import Instances
from pages.cloud.security_groups import SecurityGroups
from pages.cloud.flavors import Flavors


class Clouds(Base):
    submenus = {
        "ems_cloud": Providers,
        "availability_zone": AvailabilityZones,
        "flavor": Flavors,
        "security_group": SecurityGroups,
        "vm_cloud": Instances,
    }

# Expose the submenu pages on the Clouds class for convenience
for page in Clouds.submenus.values():
    setattr(Clouds, page.__name__, page)
