from pages.base import Base
from selenium.webdriver.common.by import By

# pylint: disable=R0904

class Detail(Base):
    '''The Cloud Providers Detail page'''
    _page_title = 'CloudForms Management Engine: Cloud Providers'
    _provider_detail_name_locator = (
            By.XPATH, '//*[@id="accordion"]/div[1]/div[1]/a')
    _details_locator = (By.CSS_SELECTOR, 'div#textual_div')

    @property
    def details(self):
        '''Details region

        Returns a Details region
        '''
        from pages.regions.details import Details
        root_element = self.selenium.find_element(*self._details_locator)
        return Details(self.testsetup, root_element)

    @property
    def name(self):
        '''Name of the provider'''
        return self.selenium.find_element(
                *self._provider_detail_name_locator).get_attribute(
                        'title').encode('utf-8')

    @property
    def hostname(self):
        '''Hostname of the provider'''
        return self.details.get_section('Properties').get_item(
                'Hostname').value

    @property
    def zone(self):
        '''Zone of the provider'''
        return self.details.get_section('Smart Management').get_item(
                'Managed by Zone').value

    @property
    def credentials_validity(self):
        '''Credentials validity flag'''
        return self.details.get_section('Authentication Status').get_item(
                'Default Credentials').value

    #def all_vms(self):
    #    '''VMs list
    #
    #    Returns cloud_subpages.instances page
    #    '''
    #    self.details.get_section('Relationships').click_item('Instances')
    #    self._wait_for_results_refresh()
    #    from pages.cloud.instances import Instances
    #    return Instances(self.testsetup)
    