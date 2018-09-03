from cfme.utils.log import logger
from cfme.utils import conf
from webdriver_kaifuku import BrowserManager


class Implementation(object):
    """UI implementation using the normal ux"""

    navigator = None

    def __init__(self, owner):
        self.owner = owner
        self.manager = BrowserManager.from_conf(conf.env.get('browser', {}))

    @property
    def appliance(self):
        return self.owner

    def __str__(self):
        return 'ViaUI'

    def open_browser(self):
        # TODO: self.appliance.server.address() instead of None
        browser = self.manager.ensure_open()
        browser.get(self.appliance.server.address())

    def quit_browser(self):
        self.manager.quit()
        self._reset_cache()

    def _reset_cache(self):
        try:
            del self.widgetastic
        except AttributeError:
            pass

    def create_view(self, view_class, additional_context=None):
        """Method that is used to instantiate a Widgetastic View.

        Views may define ``LOCATION`` on them, that implies a :py:meth:`force_navigate` call with
        ``LOCATION`` as parameter.

        Args:
            view_class: A view class, subclass of ``widgetastic.widget.View``
            additional_context: Additional informations passed to the view (user name, VM name, ...)
                which is also passed to the :py:meth:`force_navigate` in case when navigation is
                requested.

        Returns:
            An instance of the ``view_class``
        """
        additional_context = additional_context or {}
        view = view_class(
            self.widgetastic,
            additional_context=additional_context,
            logger=logger)

        return view
