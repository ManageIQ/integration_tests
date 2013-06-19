'''
Created on May 31, 2013

@author: bcrochet
'''
from pages.base import Base
from selenium.webdriver.common.by import By

class ManagementSystemsDetail(Base):
    '''The Management Systems Detail page'''
    _page_title = 'CloudForms Management Engine: Management Systems'
    _management_system_detail_name_locator = (
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
        '''Name of the management system'''
        return self.selenium.find_element(
                *self._management_system_detail_name_locator).get_attribute(
                        'title').encode('utf-8')

    @property
    def hostname(self):
        '''Hostname of the management system'''
        return self.details.get_section('Properties').get_item(
                'Hostname').value

    @property
    def zone(self):
        '''Zone of the managment system'''
        return self.details.get_section('Smart Management').get_item(
                'Managed by Zone').value

    @property
    def credentials_validity(self):
        '''Credentials validity flag'''
        return self.details.get_section('Authentication Status').get_item(
                'Default Credentials').value

    @property
    def vnc_port_range(self):
        '''VNC port range

        Returns a dictionary with start and end keys
        '''
        element_text = self.details.get_section('Properties').get_item(
                'Host Default VNC Port Range').value
        start, end = element_text.encode('utf-8').split('-')
        return { 'start': int(start), 'end': int(end) }

    def all_vms(self):
        '''VMs list

        Returns Services.VirtualMachines pages
        '''
        self.details.get_section('Relationships').click_item('VMs')
        self._wait_for_results_refresh()
        from pages.services import Services
        return Services.VirtualMachines(self.testsetup)


