""" A model of Workloads page in CFME
"""

from cfme.web_ui import accordion, menu, Tree


visible_tree = Tree("//div[@class='dhxcont_global_content_area']"
                    "[not(contains(@style, 'display: none'))]/div/div/div"
                    "/ul[@class='dynatree-container']")

menu.nav.add_branch(
    "services_workloads",
    {
        "service_vms_instances":
        [
            lambda _: accordion.tree("VMs & Instances", "All VMs & Instances"),
            {
                "service_vms_instances_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "service_vms_instances_filter":
                        lambda ctx: visible_tree.click_path(ctx["filter_name"])
                    }
                ]
            }
        ],

        "service_templates_images":
        [
            lambda _: (accordion.tree("Templates & Images", "All Templates & Images")),
            {
                "service_templates_images_filter_folder":
                [
                    lambda ctx: visible_tree.click_path(ctx["folder_name"]),
                    {
                        "service_templates_images_filter":
                        lambda ctx: visible_tree.click_path(ctx["filter_name"])
                    }
                ]
            }
        ]
    }
)
