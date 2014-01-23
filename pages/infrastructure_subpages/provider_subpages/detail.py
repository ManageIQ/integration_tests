'''
Created on May 31, 2013

@author: bcrochet
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from pages.infrastructure_subpages.vms_subpages.timelines import Timelines
from pages.infrastructure_subpages.vms_subpages.virtual_machines import VirtualMachines


class ProvidersDetail(Base):
    '''The Infrastructure Providers Detail page'''
    _page_title = 'CloudForms Management Engine: Infrastructure Providers'
    _provider_detail_name_locator = (By.XPATH, '//*[@id="accordion"]/div[1]/div[1]/a')
    _details_locator = (By.CSS_SELECTOR, 'div#textual_div')
    _configuration_button_locator = (By.CSS_SELECTOR,
        "div.dhx_toolbar_btn[title='Configuration']")
    _refresh_relationships_locator = (By.CSS_SELECTOR,
        "table.buttons_cont img[src='/images/toolbars/refresh.png']")
    _timelines_button_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title=" +
            "'Show Timelines for this Infrastructure Provider']")
    _monitoring_button_locator = (
        By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Monitoring'] > div")

    @property
    def refresh_relationships_button(self):
        '''The refresh_relationships button'''
        return self.selenium.find_element(*self._refresh_relationships_locator)

    @property
    def monitoring_button(self):
        return self.selenium.find_element(*self._monitoring_button_locator)

    @property
    def configuration_button(self):
        '''The Configuration button'''
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def timelines_button(self):
        return self.selenium.find_element(*self._timelines_button_locator)

    def click_on_refresh_relationships(self, cancel=False):
        self.configuration_button.click()
        self.refresh_relationships_button.click()
        self.handle_popup(cancel)
        self._wait_for_results_refresh()
        return "Refresh Infrastructure Providers initiated" in self.flash.message

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
        return self.selenium.find_element(*self._provider_detail_name_locator).get_attribute(
            'title').encode('utf-8')

    @property
    def hostname(self):
        '''Hostname of the provider'''
        return self.details.get_section('Properties').get_item('Hostname').value

    @property
    def zone(self):
        '''Zone of the provider'''
        return self.details.get_section('Smart Management').get_item('Managed by Zone').value

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
        return {'start': int(start), 'end': int(end)}

    @property
    def cluster_count(self):
        '''Count of clusters'''
        return self.details.get_section('Relationships').get_item('Clusters').value

    @property
    def datastore_count(self):
        '''Count of datastores'''
        return self.details.get_section('Relationships').get_item('Datastores').value

    @property
    def host_count(self):
        '''Count of hosts'''
        return self.details.get_section('Relationships').get_item('Hosts').value

    @property
    def vm_count(self):
        '''Count of VMs'''
        return self.details.get_section('Relationships').get_item('VMs').value

    def do_stats_match(self, host_stats, detailed=False):
        core_stats = False
        if int(self.host_count) == host_stats['num_host'] and \
           int(self.datastore_count) == host_stats['num_datastore'] and \
           int(self.cluster_count) == host_stats['num_cluster']:
            core_stats = True

        if core_stats and not detailed:
            return True
        elif detailed:
            if core_stats and int(self.cluster_count) == host_stats['num_cluster']:
                return True

        self.selenium.refresh()
        return False

    def all_vms(self):
        '''VMs list

        Returns Infrastructure.VirtualMachines pages
        '''
        self.details.get_section('Relationships').click_item('VMs')
        self._wait_for_results_refresh()
        return VirtualMachines(self.testsetup)

    def all_clusters(self):
        '''Clusters list

        Returns Infrastructure.Clusters pages
        '''
        self.details.get_section('Relationships').click_item('Clusters')
        self._wait_for_results_refresh()
        from pages.infrastructure import Infrastructure
        return Infrastructure.Clusters(self.testsetup)

    def all_datastores(self):
        '''Datastores list

        Returns Infrastructure.Datastores pages
        '''
        self.details.get_section('Relationships').click_item('Datastores')
        self._wait_for_results_refresh()
        from pages.infrastructure import Infrastructure
        return Infrastructure.Datastores(self.testsetup)

    def all_hosts(self):
        '''Hosts list

        Returns Hosts pages
        '''
        self.details.get_section('Relationships').click_item('Hosts')
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.hosts import Hosts
        return Hosts(self.testsetup)

    def all_templates(self):
        '''Templates list

        Returns Infrastructure.VirtualMachines pages
        '''
        self.details.get_section('Relationships').click_item('Templates')
        self._wait_for_results_refresh()
        return VirtualMachines(self.testsetup)

    def click_on_timelines(self):
        self.monitoring_button.click()
        self.timelines_button.click()
        self._wait_for_results_refresh()
        return Timelines(self.testsetup)
