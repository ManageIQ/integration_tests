from pages.base import Base
from selenium.webdriver.common.by import By

# pylint: disable=R0904


class Detail(Base):
    """The Cloud Providers Detail page"""
    _page_title = 'CloudForms Management Engine: Cloud Providers'
    _provider_detail_name_locator = (By.XPATH, '//*[@id="accordion"]/div[1]/div[1]/a')
    _details_locator = (By.CSS_SELECTOR, 'div#textual_div')

    @property
    def details(self):
        """Details region

        Returns a Details region
        """
        from pages.regions.details import Details
        root_element = self.selenium.find_element(*self._details_locator)
        return Details(self.testsetup, root_element)

    @property
    def name(self):
        """Name of the provider"""
        return self.selenium.find_element(*self._provider_detail_name_locator)\
            .get_attribute('title').encode('utf-8')

    @property
    def hostname(self):
        """Hostname of the provider"""
        return self.details.get_section('Properties')\
            .get_item('Hostname').value

    @property
    def zone(self):
        """Zone of the provider"""
        return self.details.get_section('Smart Management')\
            .get_item('Managed by Zone').value

    @property
    def credentials_validity(self):
        """Credentials validity flag"""
        return self.details.get_section('Authentication Status')\
            .get_item('Default Credentials').value

    def _all_the_things(self, relationship, pagename=None):
        if pagename is None:
            # Assume pagename == relationship link name
            pagename = relationship
        self.details.get_section('Relationships').click_item(relationship)
        from pages import cloud
        Page = getattr(cloud, pagename)
        return Page(self.testsetup)

    def all_instances(self):
        """VMs list

        Returns cloud Instances page
        """
        return self._all_the_things('Instances')

    def all_images(self):
        """Images list

        Returns cloud Images page
        """
        return self._all_the_things('Images')

    def all_azs(self):
        """Availability Zones list

        Returns cloud AvailabilityZones page
        """
        return self._all_the_things('Availability Zones',
            pagename='AvailabilityZones')

    def all_flavors(self):
        """Flavors list

        Returns cloud Flavors page
        """
        return self._all_the_things('Flavors')
