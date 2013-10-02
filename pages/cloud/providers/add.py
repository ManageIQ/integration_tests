from selenium.webdriver.common.by import By
from pages.cloud.providers.common_form import AddFormCommon

# pylint: disable=C0103
# pylint: disable=R0913
# pylint: disable=R0904


class Add(AddFormCommon):
    '''Cloud Providers - Add an Cloud Provider page'''
    _page_title = 'CloudForms Management Engine: Cloud Providers'

    _provider_add_button_locator = (
            By.CSS_SELECTOR,
            "img[alt='Add this Cloud Provider']")

    @property
    def add_button(self):
        '''Add button

        Returns a WebElement'''
        return self.get_element(*self._provider_add_button_locator)

    def _new_provider_fill_data_with_creds(
            self,
            name,
            hostname,
            cred_type,
            ip_address,
            username,
            password):
        '''Fill a cloud provider with individual args'''
        self.fill_field_element(name, self.name)

        if cred_type == 'default':
            self.update_default_creds(username, password, password)
        elif cred_type == 'amqp':
            self.fill_field_element(hostname, self.hostname)
            self.fill_field_element(ip_address, self.ipaddress)
            self.update_amqp_creds(username, password, password)
        else:
            raise Exception("Unknown cloud cred type")

    def new_provider_fill_data_amqp_creds(
            self,
            name,
            hostname,
            ip_address,
            user_id,
            password):
        '''Fill a cloud provider form including amqp credentials'''
        self._new_provider_fill_data_with_creds(
            name,
            hostname,
            'amqp',
            ip_address,
            user_id,
            password)

    def new_provider_fill_data_default_creds(
            self,
            name,
            hostname,
            ip_address,
            user_id,
            password):
        '''Fill a cloud provider form with default credentials'''
        self._new_provider_fill_data_with_creds(
            name,
            hostname,
            'default',
            ip_address,
            user_id,
            password)

    def add_ec2_provider(self, provider, region):
        '''Fill and click on add for a EC2 Cloud Provider'''
        self.select_provider_type("Amazon EC2")
        self.select_amazon_region(region)
        self._fill_provider(provider)
        return self.click_on_add()

    def add_openstack_provider(self, provider):
        '''Fill and click on add for a RHOS Cloud Provider'''
        self.select_provider_type("OpenStack")
        self._fill_provider(provider)
        return self.click_on_add()

    def add_provider(self, provider):
        '''Generic add cloud provider.

        Will determine the correct cloud provider to add'''
        if "ec2" in provider["type"]:
            return self.add_ec2_provider(provider, provider["region"])
        elif "openstack" in provider["type"]:
            return self.add_openstack_provider(provider)
        raise Exception("Unknown cloud provider type")

    def add_provider_with_bad_credentials(self, provider):
        '''Add a cloud provider and click verify,
        expecting bad creds'''
        if "ec2" in provider["type"]:
            self.select_provider_type("Amazon EC2")
            self.select_amazon_region()
        elif "openstack" in provider["type"]:
            self.select_provider_type("OpenStack")
        self._fill_provider(provider)
        self._wait_for_visible_element(
                *self._provider_credentials_verify_button_locator)
        self.click_on_credentials_verify()
        self._wait_for_results_refresh()
        return self

    def select_provider_type(self, provider_type):
        '''Select a cloud provider type from the dropdown,
        and wait for the page to refresh'''
        self.select_dropdown(
                provider_type,
                *self._provider_type_locator)

        if provider_type == 'Amazon EC2':
            self._wait_for_visible_element(*self._amazon_region_locator)
        else:
            self._wait_for_visible_element(*self._provider_ipaddress_locator)

        return Add(self.testsetup)

    def click_on_add(self):
        '''Click on the add button'''
        self.add_button.click()
        from pages.cloud.providers import Providers
        return Providers(self.testsetup)
