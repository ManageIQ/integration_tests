from typing import TypeVar

from cfme.utils.browser import manager
from cfme.utils.log import logger

# A hack to workaround problem with circular import of modules
# for the IPAppliance class
T = TypeVar('T')


class Implementation:
    """UI implementation using the normal ux"""

    navigator = None

    def __init__(self, owner: T):
        self.owner = owner

    @property
    def appliance(self):
        return self.owner

    def __str__(self):
        return 'ViaUI'

    def open_browser(self, url_key=None):
        # TODO: self.appliance.server.address() instead of None
        return manager.ensure_open(url_key)

    def quit_browser(self):
        manager.quit()
        try:
            del self.widgetastic
        except AttributeError:
            pass

    def _reset_cache(self):
        try:
            del self.widgetastic
        except AttributeError:
            pass

    def create_view(self, view_class, additional_context=None, wait=None):
        """Method that is used to instantiate a Widgetastic View.

        Views may define ``LOCATION`` on them, that implies a :py:meth:`force_navigate` call with
        ``LOCATION`` as parameter.

        Args:
            view_class: A view class, subclass of ``widgetastic.widget.View``
            additional_context: Additional informations passed to the view (user name, VM name, ...)
                which is also passed to the :py:meth:`force_navigate` in case when navigation is
                requested.
            wait: time to wait for view to show up
        Returns:
            An instance of the ``view_class``
        """
        additional_context = additional_context or {}
        view = view_class(
            self.widgetastic,
            additional_context=additional_context,
            logger=logger)
        if wait:
            view.wait_displayed(timeout=wait)
        return view
