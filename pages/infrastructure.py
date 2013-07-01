# -*- coding: utf-8 -*-

from pages.base import Base
from pages.infrastructure_subpages.providers import Providers
from pages.regions.policy_menu import PolicyMenu
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.quadicons import Quadicons
from selenium.webdriver.common.by import By
import re

class Infrastructure(Base):
    @property
    def submenus(self):
        return {"ems_infra" : Providers,
                "ems_cluster"       : Infrastructure.Clusters,
                "host"              : Infrastructure.Hosts,
                "storage"           : Infrastructure.Datastores,
                "pxe"               : Infrastructure.PXE
                }

    class Clusters(Base, PolicyMenu):
        _page_title = 'CloudForms Management Engine: Clusters'

        @property
        def icon(self):
            return Quadicons(self.testsetup)

        @property
        def accordion_region(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)

        def select_cluster(self, cluster_name):
            self.icon.get_quadicon_by_title(cluster_name).mark_checkbox()

        def click_cluster(self, cluster_name):
            self.icon.get_quadicon_by_title(cluster_name).click()
            self._wait_for_results_refresh()
            return Infrastructure.ClustersDetail(self.testsetup)

        @property
        def taskbar(self):
            from pages.regions.taskbar.taskbar import Taskbar
            return Taskbar(self.testsetup)

    class ClustersDetail(Base, PolicyMenu):
        _page_title = 'CloudForms Management Engine: Clusters'
        _cluster_detail_name_locator = (By.XPATH,
                '//*[@id="accordion"]/div[1]/div[1]/a')
        _details_locator = (By.CSS_SELECTOR, "div#textual_div")

        @property
        def details(self):
            from pages.regions.details import Details
            root_element = self.selenium.find_element(*self._details_locator)
            return Details(self.testsetup, root_element)

        @property
        def name(self):
            return self.selenium.find_element(
                    *self._cluster_detail_name_locator).text.encode('utf-8')

        @property
        def provider(self):
            return self.details.get_section("Relationships").get_item(
                    "Provider").value

        @property
        def datacenter(self):
            return self.details.get_section("Relationships").get_item(
                    "Datacenter").value

        @property
        def host_count(self):
            return self.details.get_section("Relationships").get_item(
                    "Hosts").value

    class Hosts(Base, PolicyMenu):
        _page_title = 'CloudForms Management Engine: Hosts'

        @property
        def quadicon_region(self):
            return Quadicons(
                    self.testsetup, Infrastructure.Hosts.HostQuadIconItem)

        @property
        def accordion_region(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)

        def select_host(self, host_name):
            self.quadicon_region.get_quadicon_by_title(
                    host_name).mark_checkbox()

        @property
        def taskbar(self):
            from pages.regions.taskbar.taskbar import Taskbar
            return Taskbar(self.testsetup)

        class HostQuadIconItem(QuadiconItem):
            @property
            def vm_count(self):
                return self._root_element.find_element(
                        *self._quad_tl_locator).text

            @property
            def current_state(self):
                image_src = self._root_element.find_element(
                        *self._quad_tr_locator).find_element_by_tag_name(
                                "img").get_attribute("src")
                return re.search(r'.+/currentstate-(.+)\.png',
                        image_src).group(1)

            @property
            def vendor(self):
                image_src = self._root_element.find_element(
                        *self._quad_bl_locator).find_element_by_tag_name(
                                "img").get_attribute("src")
                return re.search(r'.+/vendor-(.+)\.png', image_src).group(1)

            @property
            def valid_credentials(self):
                image_src = self._root_element.find_element(
                        *self._quad_br_locator).find_element_by_tag_name(
                                "img").get_attribute("src")
                return 'checkmark' in image_src

            # def click(self):
            #    self._root_element.click()
            #    self._wait_for_results_refresh()
            #    return Infrastructure.HostsDetail(self.testsetup)

    class Datastores(Base, PolicyMenu):
        _page_title = 'CloudForms Management Engine: Datastores'

        @property
        def quadicon_region(self):
            return Quadicons(self.testsetup, 
                    Infrastructure.Datastores.DatastoreQuadIconItem)

        @property
        def accordion_region(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)

        def select_datastore(self, datastore_name):
            self.quadicon_region.get_quadicon_by_title(
                    datastore_name).mark_checkbox()

        def click_datastore(self, datastore_name):
            self.quadicon_region.get_quadicon_by_title(datastore_name).click()
            self._wait_for_results_refresh()
            return Infrastructure.DatastoresDetail(self.testsetup)

        @property
        def taskbar(self):
            from pages.regions.taskbar.taskbar import Taskbar
            return Taskbar(self.testsetup)

        class DatastoreQuadIconItem(QuadiconItem):

            @property
            def vm_count(self):
                return self._root_element.find_element(
                        *self._quad_tr_locator).text

            @property
            def host_count(self):
                return self._root_element.find_element(
                        *self._quad_bl_locator).text

    class DatastoresDetail(Base, PolicyMenu):
        _page_title = 'CloudForms Management Engine: Datastores'
        _datastore_detail_name_locator = (By.XPATH,
                '//*[@id="accordion"]/div[1]/div[1]/a')
        _details_locator = (By.CSS_SELECTOR, "div#textual_div")

        @property
        def details(self):
            from pages.regions.details import Details
            root_element = self.selenium.find_element(*self._details_locator)
            return Details(self.testsetup, root_element)

        @property
        def name(self):
            return self.selenium.find_element(
                    *self._datastore_detail_name_locator).text.encode('utf-8')

        @property
        def ds_type(self):
            return self.details.get_section("Properties").get_item(
                    "Datastore Type").value

    class PXE(Base):
        _page_title = 'CloudForms Management Engine: PXE'

        _add_template_locator = (By.CSS_SELECTOR,
                "tr.tr_btn[title='Add a New Customization Template']")
        _add_iso_datastore_locator = (By.CSS_SELECTOR,
                "tr.tr_btn[title='Add a New ISO Datastore']")
        _copy_template_locator = (
                By.CSS_SELECTOR,
                "tr.tr_btn[title='Copy this Customization Template']")
        _refresh_locator = (
                By.CSS_SELECTOR,
                "tr.tr_btn[title='Refresh this PXE Server']")
        _pxe_image_names_locator = (
                By.CSS_SELECTOR,
                "div#pxe_info_div > fieldset > table[class='style3'] > tbody")

        _add_pxe_locator = (
                By.CSS_SELECTOR, "tr.tr_btn[title='Add a New PXE Server']")

        @property
        def accordion_region(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
            return Accordion(self.testsetup, LegacyTreeAccordionItem)

        @property
        def center_buttons(self):
            from pages.regions.taskbar.center import CenterButtons
            return CenterButtons(self.testsetup)

        def click_on_add_template(self):
            self.selenium.find_element(*self._add_template_locator).click()
            self._wait_for_results_refresh()
            # return Infrastructure.PXE(self.testsetup)
            return Infrastructure.PXEAddTemplate(self.testsetup)

        def click_on_add_pxe_server(self):
            self.selenium.find_element(*self._add_pxe_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.PXEAddServer(self.testsetup)

        def click_on_refresh(self):
            self.selenium.find_element(*self._refresh_locator).click()

        def pxe_image_names(self):
            element_text = self.selenium.find_element(
                    *self._pxe_image_names_locator).text
            lines = element_text.split('\n')
            names = []
            for line in lines:
                name, space, test = line.partition(' ')
                names.append(name)
            return names

        def click_on_add_iso_datastore(self):
            self.selenium.find_element(*self._add_iso_datastore_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.PXEAddISODatastore(self.testsetup)

    class PXEAddISODatastore(Base):
        _provider_locator = (By.CSS_SELECTOR, "select#ems_id")
        _add_button_locator = (By.CSS_SELECTOR,
                "div#buttons_on > ul > li > img[alt='Add']")
        _datastore_name_locator = (By.CSS_SELECTOR,
                "table[class='style3'] > tbody")

        def select_provider(self, name):
            self.select_dropdown(name, *self._provider_locator)
            self._wait_for_results_refresh()

        def click_on_add(self):
            self.selenium.find_element(*self._add_button_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.PXEAdded(self.testsetup)

        def datastore_name(self):
            element_text = self.selenium.find_element(
                    *self._datastore_name_locator).text
            return element_text

    class PXEAddTemplate(Base):

        _template_type_locator = (By.CSS_SELECTOR, "select#typ")

        def new_pxe_template_select_type(self,
                                         template_type="Kickstart"
                                        ):
            self.select_dropdown(template_type, *self._template_type_locator)
            return Infrastructure.PXETemplateData(self.testsetup)

    class PXETemplateData(Base):

        _template_name_locator = (By.CSS_SELECTOR, "input#name")
        _template_description_locator = (By.CSS_SELECTOR, "input#description")
        _template_script_locator = (By.CSS_SELECTOR,
                "div[class='CodeMirror'] > div > textarea")
        _image_type_locator = (By.CSS_SELECTOR, "select#img_typ")
        _add_button_locator = (
                By.CSS_SELECTOR,
                "div#buttons_on > ul > li > img[title='Add']")

        # Template type is selected independently.
        # This is because it modifies the page, and we need to wait for the 
        # modification to take effect.
        # No visible elements are modified, _wait_for_visible_element and 
        # _wait_for_results_refresh are out of the question.
        def new_pxe_template_fill_data(
                                       self,
                                       name="rhel",
                                       description="my description",
                                       image_type="RHEL-6",
                                       template_type="",
                                       # TODO treat this as a local file?
                                       # assume anaconda.ks_template
                                       script="anaconda.ks"
                                       ):
            # name
            self.selenium.find_element(
                    *self._template_name_locator).send_keys(name)
            # description
            self.selenium.find_element(
                    *self._template_description_locator).send_keys(description)
            # image type
            self.select_dropdown(image_type, *self._image_type_locator)
            # script
            self.selenium.find_element(
                    *self._template_script_locator).send_keys(script)

        def click_on_add(self):
            self.selenium.find_element(*self._add_button_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.PXEAdded(self.testsetup)

    class PXEAdded(Base):

        _datastore_name_locator = (By.CSS_SELECTOR,
                "table[class='style3'] > tbody")

        def datastore_name(self):
            element_text = self.selenium.find_element(
                    *self._datastore_name_locator).text
            text = element_text.split('\n')
            return text[0]

    class PXEAddServer(Base):

        _pxe_depot_type_locator = (By.CSS_SELECTOR, "select#log_protocol")
        _pxe_uri_locator = (By.CSS_SELECTOR, "input#uri")

        def select_depot_type(self, depot_type):
            self.select_dropdown(depot_type, *self._pxe_depot_type_locator)
            # Wait for the form to refresh (show URI element) before continuing
            self._wait_for_visible_element(*self._pxe_uri_locator)
            return Infrastructure.PXERefreshed(self.testsetup)

    class PXERefreshed(Base):

        _add_button_locator = (
                By.CSS_SELECTOR, "div#buttons_on > ul > li > img[title='Add']")
        _pxe_name_locator = (By.CSS_SELECTOR, "input#name")
        _pxe_uri_locator = (By.CSS_SELECTOR, "input#uri")
        _pxe_access_url_locator = (By.CSS_SELECTOR, "input#access_url")
        _pxe_directory_locator = (By.CSS_SELECTOR, "input#pxe_directory")
        _pxe_windows_images_directory_locator = (
                By.CSS_SELECTOR, "input#windows_images_directory")
        _pxe_customization_directory_locator = (
                By.CSS_SELECTOR, "input#customization_directory")
        _pxe_image_menus_filename_locator = (
                By.CSS_SELECTOR, "input#pxemenu_0")

        # empty depot_type parameter needed to successfuly run this function 
        # from a test this is because we have all the data in cfme_data file
        # depot type needs to be set up separatelly, but also needs to be here
        def new_pxe_server_fill_data(
                                     self,
                                     depot_type="",
                                     name="pxe_server",
                                     uri="127.0.0.1/var/www/html/pub/miq/ipxe/",
                                     access_url="http://127.0.0.1/ipxe",
                                     pxe_dir="pxe",
                                     windows_img_dir="sources/microsoft",
                                     customization_dir="customization",
                                     pxe_img_menus_filename="menu.php"
                                     ):
            # name
            self.selenium.find_element(*self._pxe_name_locator).send_keys(name)
            # uri
            self.selenium.find_element(*self._pxe_uri_locator).send_keys(uri)
            # access url
            self.selenium.find_element(
                    *self._pxe_access_url_locator).send_keys(access_url)
            # pxe directory
            self.selenium.find_element(
                    *self._pxe_directory_locator).send_keys(pxe_dir)
            # windows images directory
            self.selenium.find_element(
                    *self._pxe_windows_images_directory_locator).send_keys(
                            windows_img_dir)
            # customization directory
            self.selenium.find_element(
                    *self._pxe_customization_directory_locator).send_keys(
                            customization_dir)
            # pxe image menus filename
            self.selenium.find_element(
                    *self._pxe_image_menus_filename_locator).send_keys(
                            pxe_img_menus_filename)

        def click_on_add(self):
            self.selenium.find_element(*self._add_button_locator).click()
            self._wait_for_results_refresh()
            return Infrastructure.PXEAdded(self.testsetup)

