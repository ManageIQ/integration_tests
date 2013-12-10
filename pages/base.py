#!/usr/bin/env python
# -*- coding: utf-8 -*-
import fixtures.pytest_selenium as sel
from pages.region import Region
from selenium.webdriver.common.by import By

base = Region(locators={'csrf_meta': (By.CSS_SELECTOR, "meta[name=csrf-token]")})


class Flash(Region):
    def get_message(self):
        if sel.is_displayed(self.message):
            return sel.text(self.message)
        else:
            return None

flash = Flash(locators={'message': (By.XPATH, "//div[@id='flash_text_div' or @id='flash_div']")})

# def current_subpage():
#     submenu_name = sel.find_element_by_tag_name("body").get_attribute("id")
#     return self.submenus[submenu_name](self.testsetup)  # IGNORE:E1101


def csrf_token():
    return sel.get_attribute(base.csrf_meta, 'content')


def set_csrf_token(value):
    # Changing the CSRF Token on the fly via the DOM by iterating
    # over the meta tags
    script = '''
        var elements = document.getElementsByTagName("meta");
        for (var i=0, element; element = elements[i]; i++) {
            var ename = element.getAttribute("name");
            if (ename != null && ename.toLowerCase() == "csrf-token") {
                element.setAttribute("content", "%s");
                break;
            }
        }
    ''' % value
    sel.execute_script(script)


def go_to_login_page():
    sel.get(sel.baseurl())


header_region = Region(locators=
                       {"logout_link": (By.CSS_SELECTOR, "a[title='Click to Logout']"),
                        "user_indicator": (By.CSS_SELECTOR, "div#page_header_div li.dropdown"),
                        "user_options_button": (By.CSS_SELECTOR, "div#page_header_div b.caret"),
                        "user_options": (By.CSS_SELECTOR, "ul#user_options_div"),
                        "site_navigation_menus": (By.CSS_SELECTOR, "div.navbar > ul > li")})


def logout():
    sel.move_to_element(header_region.user_options)
    sel.click(header_region.logout_link)


# def site_navigation_menu(value):
#     # used to access on specific menu
#     for menu in header_region.site_navigation_menus:
#         if menu.name == value:
#             return menu
#             raise Exception("Menu not found: '%s'. Menus: %s" %
#                             (value, [menu.name for menu in header_region.site_navigation_menus]))


# def site_navigation_menus(self):
#     from pages.regions.header_menu import HeaderMenu
#     return [HeaderMenu(self.testsetup, web_element) for web_element
#             in sel.find_elements(*self._site_navigation_menus_locator)]
