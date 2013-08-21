from pages.regions.quadiconitem import QuadiconItem
import re

# pylint: disable=R0904

class CloudProviderQuadIcon(QuadiconItem):
    '''Represents a provider quadicon'''

    @property
    def vendor(self):
        '''Which provider vendor?'''
        image_src = self._root_element.find_element(
                *self._quad_bl_locator).find_element_by_tag_name(
                        "img").get_attribute("src")
        return re.search(r'.+/vendor-(.+)\.png', image_src).group(1)

    @property
    def valid_credentials(self):
        '''Does the provider have valid credentials?'''
        image_src = self._root_element.find_element(
                *self._quad_br_locator).find_element_by_tag_name(
                        "img").get_attribute("src")
        return 'checkmark' in image_src

    def click(self):
        '''Click on the provider quadicon'''
        self._root_element.click()
        self._wait_for_results_refresh()
        from pages.cloud.providers.details import Detail
        return Detail(self.testsetup)
