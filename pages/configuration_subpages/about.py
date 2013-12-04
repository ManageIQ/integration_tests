from pages.region import Region
import pages.regions.list as list
from selenium.webdriver.common.by import By
import fixtures.pytest_selenium as sel

about_page = Region(
    locators={'session_info': (By.CSS_SELECTOR, "dl.col2 > dd > fieldset > table.style1 > tbody"),
              'page_links': (By.XPATH, "//p[@class='legend']/../a"),
              'version': (By.XPATH, "//td[.='Version']../td[2]")},
    title="CloudForms Management Engine: About")


def get(key):
    return list.as_dict(list.extract_table(about_page.session_info))[key][0]


def version():
    return tuple(get('Version').split("."))


def server_name():
    return get('Server Name')


def docs_links():
    page_links = sel.elements(about_page.page_links)
    links = []
    # assume we have an icon, followed by text link
    # as not in a table and don't want to use sibling find
    # this is quickest way for now
    num_docs = len(page_links) / 2
    for index in range(num_docs):
        n_index = index * 2
        icon_url = page_links[n_index].get_attribute('href')
        icon_img = page_links[n_index].find_elements_by_tag_name('img')
        icon_alt = icon_img[0].get_attribute('alt')
        icon_title = page_links[n_index].get_attribute('title')
        text_url = page_links[n_index + 1].get_attribute('href')
        text_title = page_links[n_index + 1].text
        links.append({
            "icon_url": icon_url,
            "icon_title": icon_title,
            "icon_alt": icon_alt,
            "text_url": text_url,
            "text_title": text_title})
    return links
