# -*- coding: utf-8 -*-
""" A model of Workloads page in CFME
"""
from functools import partial
from cfme.web_ui import accordion, menu

vm_instances_tree = partial(accordion.tree, "VMs & Instances")
templates_images_tree = partial(accordion.tree, "Templates & Images")


@menu.extend_nav
class services_workloads:
    def service_vms_instances_filter_folder(ctx):
        vm_instances_tree("All VMs & Instances", ctx["folder_name"])

    def service_vms_instances_filter(ctx):
        vm_instances_tree("All VMs & Instances", ctx["folder_name"], ctx["filter_name"])

    def service_templates_images_filter_folder(ctx):
        templates_images_tree("All Templates & Images", ctx["folder_name"])

    def service_templates_images_filter(ctx):
        templates_images_tree("All Templates & Images", ctx["folder_name"], ctx["filter_name"])
