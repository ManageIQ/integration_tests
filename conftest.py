# Markers, Meta, and fixture plugins

pytest_plugins = [
    # Markers
    "cfme.markers.composite",
    "cfme.markers.crud",
    "cfme.markers.destructive",
    "cfme.markers.env",
    "cfme.markers.fixtureconf",
    "cfme.markers.isolation",
    "cfme.markers.manual",
    "cfme.markers.marker_filters",
    "cfme.markers.meta",
    "cfme.markers.polarion",  # load before artifactor
    "cfme.markers.regression",
    "cfme.markers.requires",
    "cfme.markers.rhel_tests",
    "cfme.markers.sauce",
    "cfme.markers.serial",
    "cfme.markers.skipper",
    "cfme.markers.smoke",
    "cfme.markers.stream_excluder",
    "cfme.markers.uses",
    "cfme.markers.uncollect",
    # Meta
    "cfme.metaplugins",
    # Store and framework plugins
    "cfme.fixtures.pytest_store",  # import early
    "cfme.test_framework.sprout.plugin",
    "cfme.test_framework.appliance_hooks",
    "cfme.test_framework.appliance_police",
    "cfme.test_framework.appliance",
    "cfme.test_framework.appliance_log_collector",
    "cfme.test_framework.browser_isolation",
    "cfme.fixtures.ansible_fixtures",
    "cfme.fixtures.ansible_tower",
    # appliance plugins
    "cfme.test_framework.appliance.holder",
    "cfme.test_framework.appliance.dummy",
    "cfme.test_framework.appliance.local",
    "cfme.test_framework.appliance.default",
    "cfme.test_framework.appliance.pod",
    "cfme.test_framework.appliance.multi_region",
    "cfme.test_framework.appliance.upgraded",
    "cfme.test_framework.appliance.env",
    "cfme.fixtures.appliance_update",
    "cfme.fixtures.artifactor_plugin",
    "cfme.fixtures.authentication",
    "cfme.fixtures.automate",
    "cfme.fixtures.base",
    "cfme.fixtures.blockers",
    "cfme.fixtures.browser",
    "cfme.fixtures.bzs",
    "cfme.fixtures.candu",
    "cfme.fixtures.cfme_data",
    "cfme.fixtures.cli",
    "cfme.fixtures.datafile",
    "cfme.fixtures.depot",
    "cfme.fixtures.dev_branch",
    "cfme.fixtures.disable_forgery_protection",
    "cfme.fixtures.embedded_ansible",
    "cfme.fixtures.events",
    "cfme.fixtures.fixtureconf",
    "cfme.fixtures.generic_object",
    "cfme.fixtures.has_persistent_volume",
    "cfme.fixtures.log",
    "cfme.fixtures.maximized",
    "cfme.fixtures.model_collections",
    "cfme.fixtures.multi_region",
    "cfme.fixtures.multi_tenancy",
    "cfme.fixtures.nelson",
    "cfme.fixtures.networks",
    "cfme.fixtures.nuage",
    "cfme.fixtures.page_screenshots",
    "cfme.fixtures.parallelizer",
    "cfme.fixtures.perf",
    "cfme.fixtures.physical_switch",
    "cfme.fixtures.portset",
    "cfme.fixtures.prov_filter",
    "cfme.fixtures.provider",
    "cfme.fixtures.pxe",
    "cfme.fixtures.qa_contact",
    "cfme.fixtures.randomness",
    "cfme.fixtures.rbac",
    "cfme.fixtures.rdb",
    "cfme.fixtures.sauce",
    "cfme.fixtures.screenshots",
    "cfme.fixtures.service_fixtures",
    "cfme.fixtures.single_appliance_sprout",
    "cfme.fixtures.skip_not_implemented",
    "cfme.fixtures.smtp",
    "cfme.fixtures.soft_assert",
    "cfme.fixtures.ssh_client",
    "cfme.fixtures.tag",
    "cfme.fixtures.tccheck",
    "cfme.fixtures.templateloader",
    "cfme.fixtures.templates",
    "cfme.fixtures.terminalreporter",
    "cfme.fixtures.ui_coverage",
    "cfme.fixtures.utility_vm",
    "cfme.fixtures.update_tests",
    "cfme.fixtures.v2v_fixtures",
    "cfme.fixtures.version_info",
    "cfme.fixtures.video",
    "cfme.fixtures.virtual_machine",
    "cfme.fixtures.vm",
    "cfme.fixtures.vm_console",
    "cfme.fixtures.vporizer",
    "cfme.fixtures.xunit_tools",
]
