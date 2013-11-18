#!/usr/bin/env python

# -*- coding: utf-8 -*-
from fixtures.pytest_selenium import move_to_element, click
from pages.region import Region
from itertools import dropwhile


def menu_item(text):
    return ("//div[@class='navbar']//a[.='{}' and "
    "not(ancestor::*[contains(@style,'display: none')])]").format(text)


def make_menu_items(dct):
    return {k: menu_item(v) for k, v in dct.items()}


main_menu = Region(locators=
                   make_menu_items(
                       {'cloud_intelligence': 'Cloud Intelligence',
                        'services': 'Services',
                        'clouds': 'Services',
                        'infrastructure': 'Infrastructure',
                        'control': 'Control',
                        'automate': 'Automate',
                        'optimize': 'Optimize',
                        'configure': 'Configuration'}))

cloud_intelligence_menu = Region(locators=
                                 make_menu_items(
                                     {"dashboard": 'Dashboard',
                                      "reports": 'Reports',
                                      "usage": 'Usage',
                                      "chargeback": 'Chargeback',
                                      "timelines": 'Timelines',
                                      "rss": 'RSS'}))

services_menu = Region(locators=
                       make_menu_items(
                           {"my_services": "My Services",
                            "catalogs": "Catalogs",
                            "workloads": "Workloads",
                            "requests": "Requests"}))

clouds_menu = Region(locators=
                     make_menu_items(
                         {"providers": "Providers",
                          "availability_zones": "Availability Zones",
                          "flavors": "Flavors",
                          "security_groups": "Security Groups",
                          "instances": "Instances"}))

infrastructure_menu = Region(locators=
                             make_menu_items(
                                 {"providers": "Providers",
                                  "clusters": "Clusters",
                                  "hosts": "Hosts",
                                  "virtual_machines": "Virtual Machines",
                                  "resource_pools": "Resource Pools",
                                  "datastores": "Datastores",
                                  "repositories": "Repositories",
                                  "pxe": "PXE",
                                  "requests": "Requests"}))

control_menu = Region(locators=
                      make_menu_items(
                          {"explorer": "Explorer",
                           "simulation": "Simulation",
                           "import_export": "Import / export",
                           "log": "Log"}))

automate_menu = Region(locators=
                       make_menu_items(
                           {"explorer": "Explorer",
                            "simulation": "Simulation",
                            "customization": "Customization",
                            "import_export": "Import / Export",
                            "log": "Log",
                            "requests": "Requests"}))

optimize_menu = Region(locators=
                       make_menu_items(
                           {"utilization": "Utilization",
                            "planning": "Planning",
                            "bottlenecks": "Bottlenecks"}))

configure_menu = Region(locators=
                        make_menu_items(
                            {"my_settings": "My Settings",
                             "tasks": "Tasks",
                             "configuration": "Configuration",
                             "smartproxies": "SmartProxies",
                             "about": "About"}))


def move_to_fn(el):
    return lambda: move_to_element(el)


def click_fn(el):
    return lambda: click(el)


menu_tree = ["toplevel", lambda: None,
             [["cloud_intelligence", move_to_fn(main_menu.cloud_intelligence),
               [["dashboard", click_fn(cloud_intelligence_menu.dashboard)],
                ["reports", click_fn(cloud_intelligence_menu.reports)],
                ["usage", click_fn(cloud_intelligence_menu.usage)],
                ["chargeback", click_fn(cloud_intelligence_menu.chargeback)],
                ["timelines", click_fn(cloud_intelligence_menu.timelines)],
                ["rss", click_fn(cloud_intelligence_menu.rss)]]],
              ["services", move_to_fn(main_menu.services),
               [["my_services", click_fn(services_menu.my_services)],
                ["services_catalogs", click_fn(services_menu.catalogs)],
                ["services_workloads", click_fn(services_menu.workloads)],
                ["services_requests", click_fn(services_menu.requests)]]],
              ["clouds", move_to_fn(main_menu.clouds),
               [["clouds_providers", click_fn(clouds_menu.providers)],
                ["clouds_availability_zones", click_fn(clouds_menu.availability_zones)],
                ["clouds_flavors", click_fn(clouds_menu.flavors)],
                ["clouds_security_groups", click_fn(clouds_menu.security_groups)],
                ["clouds_instances", click_fn(clouds_menu.instances)]]],
              ["infrastructure", move_to_fn(main_menu.infrastructure),
               [["infrastructure_providers", click_fn(infrastructure_menu.providers)],
                ["infrastructure_clusters", click_fn(infrastructure_menu.clusters)],
                ["infrastructure_hosts", click_fn(infrastructure_menu.hosts)],
                ["infrastructure_virtual_machines", click_fn(infrastructure_menu.virtual_machines)],
                ["infrastructure_resource_pools", click_fn(infrastructure_menu.resource_pools)],
                ["infrastructure_datastores", click_fn(infrastructure_menu.datastores)],
                ["infrastructure_repositories", click_fn(infrastructure_menu.repositories)],
                ["infrastructure_pxe", click_fn(infrastructure_menu.pxe)],
                ["infrastructure_requests", click_fn(infrastructure_menu.requests)]]],
              ["control", move_to_fn(main_menu.control),
               [["control_explorer", click_fn(control_menu.explorer)],
                ["control_simulation", click_fn(control_menu.simulation)],
                ["control_import_export", click_fn(control_menu.import_export)],
                ["control_log", click_fn(control_menu.log)]]],
              ["automate", move_to_fn(main_menu.automate),
               [["automate_explorer", click_fn(automate_menu.explorer)],
                ["automate_simulation", click_fn(automate_menu.simulation)],
                ["automate_customization", click_fn(automate_menu.customization)],
                ["automate_import_export", click_fn(automate_menu.import_export)],
                ["automate_log", click_fn(automate_menu.log)],
                ["automate_requests", click_fn(automate_menu.requests)]]],
              ["optimize", move_to_fn(main_menu.optimize),
               [["utilization", click_fn(optimize_menu.utilization)],
                ["planning", click_fn(optimize_menu.planning)],
                ["bottlenecks", click_fn(optimize_menu.bottlenecks)]]],
              ["configure", move_to_fn(main_menu.configure),
               [["my_settings", click_fn(configure_menu.my_settings)],
                ["tasks", click_fn(configure_menu.tasks)],
                ["configuration", click_fn(configure_menu.configuration)],
                ["smartproxies", click_fn(configure_menu.smartproxies)],
                ["about", click_fn(configure_menu.about)]]]]]


def tree_find(target, tree):
    node = [[tree[0], tree[1]]]
    if tree[0] == target:
        return node
    elif len(tree) > 2:
        for child in tree[2]:
            path_below = tree_find(target, child)
            if path_below:
                return node + path_below
    return None
                

def navigate(tree, end, start=None):
    steps = tree_find(end, tree)
    if start:
        steps = dropwhile(lambda s: s[0] != start, steps)
    if len(steps) == 0:
        raise ValueError("Starting location {} not found in navigation tree.".format(start))
    for step in steps:
        print(step)
        step[1]()
