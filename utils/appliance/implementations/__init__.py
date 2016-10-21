from utils.browser import manager
from utils.log import logger


class Implementation(object):
    """UI implementation using the normal ux"""
    def __init__(self, owner):
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
