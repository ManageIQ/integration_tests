from urlparse import urlparse

from robottelo.common import conf as robo_conf
from robottelo.ui.login import Login
from robottelo.ui.navigator import Navigator
from robottelo.ui.rhci import RHCI

from utils.browser import browser, ensure_browser_open
from utils import conf


class RoboNamespace(object):
    """Container for instances of robottelo objects"""
    # robottelo UI classes to expose on instances of this class as attributes
    # key is the attr name, value is the class to instantiate
    _robo_ui_classes = {
        'navigator': Navigator,
        'login': Login,
        'rhci': RHCI,
    }
    _robo_ui_cache = {}

    def __init__(self):
        # You're in charge of opening the browser on instantiation
        robo_spoofer()

    def __getattr__(self, attr):
        if attr not in RoboNamespace._robo_ui_cache:
            RoboNamespace._robo_ui_cache[attr] = RoboNamespace._robo_ui_classes[attr](browser())
        return RoboNamespace._robo_ui_cache[attr]

    def home(self):
        """Navigate to the RHCI Web UI base URL

        Also ensures a browser is open, and returns it

        """
        return ensure_browser_open(conf.rhci.fusor_ui_url)


def robo_spoofer():
    ui_url = conf.rhci.fusor_ui_url
    # spoofs cfme_tests conf keys to support using robottelo
    conf.runtime['env']['base_url'] = ui_url

    # spoofs robottelo conf keys that we can figure out from the rhci config
    url_parts = urlparse(ui_url)
    try:
        hostname, port = url_parts.netloc.split(':')
    except ValueError:
        hostname = url_parts.netloc
        port = '443' if url_parts.scheme == 'https' else '80'
    robo_conf.properties['main.server.scheme'] = url_parts.scheme
    robo_conf.properties['main.server.hostname'] = hostname
    robo_conf.properties['main.server.port'] = port
