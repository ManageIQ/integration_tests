from widgetastic.widget import Text
from widgetastic_patternfly import Button

from cfme.base.login import BaseLoggedInPage


class CloudInsightsServicesView(BaseLoggedInPage):
    """Basic view for Red Hat Cloud/Services page."""
    title = Text('//div[@id="red_hat_cloud_services_redirect"]//h1')
    subtext = Text(locator='.//p[@id="red_hat_cloud_services_redirect_info"')
    take_me_button = Button("Take me there")

    @property
    def is_displayed(self):
        return (
            self.title.text == "Services" and self.take_me_button.is_displayed
        )
