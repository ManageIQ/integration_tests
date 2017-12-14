from widgetastic.utils import VersionPick

from cfme.automate.service_dialogs import DialogCollection as dc58  # noqa
from cfme.automate.dialogs.service_dialogs import DialogCollection as dc59  # noqa
from cfme.utils import version

collection_pick = VersionPick({
    version.LOWEST: dc58,
    '5.9': dc59})
