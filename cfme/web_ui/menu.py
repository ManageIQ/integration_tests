from cfme.fixtures.pytest_selenium import click_fn, move_to_fn
import ui_navigate as nav
from cfme.web_ui import Region


def item(text):
    return ("//div[@class='navbar']//a[normalize-space(.)='%s' and "
            "not(ancestor::*[contains(@style,'display: none')])]" % text)


def make_items(dct):
    return {k: item(v) for k, v in dct.items()}


main = Region(locators=
              make_items(
                  {'cloud_intelligence': 'Cloud Intelligence',
                   'services': 'Services',
                   'clouds': 'Clouds',
                   'infrastructure': 'Infrastructure',
                   'control': 'Control',
                   'automate': 'Automate',
                   'optimize': 'Optimize',
                   'configure': 'Configure'}))

cloud_intelligence = Region(locators=
                            make_items(
                                {"dashboard": 'Dashboard',
                                 "reports": 'Reports',
                                 "usage": 'Usage',
                                 "chargeback": 'Chargeback',
                                 "timelines": 'Timelines',
                                 "rss": 'RSS'}))

services = Region(locators=
                  make_items(
                      {"my_services": "My Services",
                       "catalogs": "Catalogs",
                       "workloads": "Workloads",
                       "requests": "Requests"}))

clouds = Region(locators=
                make_items(
                    {"providers": "Providers",
                     "availability_zones": "Availability Zones",
                     "flavors": "Flavors",
                     "security_groups": "Security Groups",
                     "instances": "Instances"}))

infrastructure = Region(locators=
                        make_items(
                            {"providers": "Providers",
                             "clusters": "Clusters",
                             "hosts": "Hosts",
                             "virtual_machines": "Virtual Machines",
                             "resource_pools": "Resource Pools",
                             "datastores": "Datastores",
                             "repositories": "Repositories",
                             "pxe": "PXE",
                             "requests": "Requests"}))

control = Region(locators=
                 make_items(
                     {"explorer": "Explorer",
                      "simulation": "Simulation",
                      "import_export": "Import / export",
                      "log": "Log"}))

automate = Region(locators=
                  make_items(
                      {"explorer": "Explorer",
                       "simulation": "Simulation",
                       "customization": "Customization",
                       "import_export": "Import / Export",
                       "log": "Log",
                       "requests": "Requests"}))

optimize = Region(locators=
                  make_items(
                      {"utilization": "Utilization",
                       "planning": "Planning",
                       "bottlenecks": "Bottlenecks"}))

configure = Region(locators=
                   make_items(
                       {"my_settings": "My Settings",
                        "tasks": "Tasks",
                        "configuration": "Configuration",
                        "smartproxies": "SmartProxies",
                        "about": "About"}))

nav_tree = {"cloud_intelligence":
            [move_to_fn(main.cloud_intelligence),
             {"dashboard": click_fn(cloud_intelligence.dashboard),
              "reports": click_fn(cloud_intelligence.reports),
              "usage": click_fn(cloud_intelligence.usage),
              "chargeback": click_fn(cloud_intelligence.chargeback),
              "timelines": click_fn(cloud_intelligence.timelines),
              "rss": click_fn(cloud_intelligence.rss)}],
            "services":
            [move_to_fn(main.services),
             {"my_services": click_fn(services.my_services),
              "services_catalogs": click_fn(services.catalogs),
              "services_workloads": click_fn(services.workloads),
              "services_requests": click_fn(services.requests)}],
            "clouds":
            [move_to_fn(main.clouds),
             {"clouds_providers": click_fn(clouds.providers),
              "clouds_availability_zones": click_fn(clouds.availability_zones),
              "clouds_flavors": click_fn(clouds.flavors),
              "clouds_security_groups": click_fn(clouds.security_groups),
              "clouds_instances": click_fn(clouds.instances)}],
            "infrastructure":
            [move_to_fn(main.infrastructure),
             {"infrastructure_providers": click_fn(infrastructure.providers),
              "infrastructure_clusters": click_fn(infrastructure.clusters),
              "infrastructure_hosts": click_fn(infrastructure.hosts),
              "infrastructure_virtual_machines": click_fn(infrastructure.virtual_machines),
              "infrastructure_resource_pools": click_fn(infrastructure.resource_pools),
              "infrastructure_datastores": click_fn(infrastructure.datastores),
              "infrastructure_repositories": click_fn(infrastructure.repositories),
              "infrastructure_pxe": click_fn(infrastructure.pxe),
              "infrastructure_requests": click_fn(infrastructure.requests)}],
            "control":
            [move_to_fn(main.control),
             {"control_explorer": click_fn(control.explorer),
              "control_simulation": click_fn(control.simulation),
              "control_import_export": click_fn(control.import_export),
              "control_log": click_fn(control.log)}],
            "automate":
            [move_to_fn(main.automate),
             {"automate_explorer": click_fn(automate.explorer),
              "automate_simulation": click_fn(automate.simulation),
              "automate_customization": click_fn(automate.customization),
              "automate_import_export": click_fn(automate.import_export),
              "automate_log": click_fn(automate.log),
              "automate_requests": click_fn(automate.requests)}],
            "optimize":
            [move_to_fn(main.optimize),
             {"utilization": click_fn(optimize.utilization),
              "planning": click_fn(optimize.planning),
              "bottlenecks": click_fn(optimize.bottlenecks)}],
            "configure":
            [move_to_fn(main.configure),
             {"my_settings": click_fn(configure.my_settings),
              "tasks": click_fn(configure.tasks),
              "configuration": click_fn(configure.configuration),
              "smartproxies": click_fn(configure.smartproxies),
              "about": click_fn(configure.about)}]}


nav.add_branch('toplevel', nav_tree)
