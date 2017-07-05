from __future__ import absolute_import
from cfme.fixtures import pytest_selenium as sel


def pull_splitter_left():
    sel.click("//span[@class='fa fa-angle-left']")


def pull_splitter_right():
    sel.click("//span[@class='fa fa-angle-right']")
