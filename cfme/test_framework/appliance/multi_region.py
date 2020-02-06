# import attr
# import pytest
#
# from cfme.fixtures import terminalreporter
# from cfme.utils.appliance import MultiRegionAppliance
#
# PLUGIN_KEY = "multi-region-appliance"
# APP_TYPE = MultiRegionAppliance.type
#
#
# def pytest_addoption(parser):
#     group = parser.getgroup("cfme")
#
#     # multi-region appliance type
#     # some providers aren't suitable for multi-region tests due to issues with floating IP and etc
#     group.addoption('--num-mr-apps-remote-nodes', action=1, type=int,
#                     dest='num-multi-region-apps-remote-nodes')
#
#
# @pytest.hookimpl
# def pytest_configure(config):
#     app_type = config.getoption('--app-type')
#     if APP_TYPE == app_type:
#         reporter = terminalreporter.reporter()
#
#         plugin = LocalAppliancePlugin()
#         config.pluginmanager.register(plugin, PLUGIN_KEY)
#
#
#
#         reporter.write_line('Retrieved Multi-Region Appliance Env', red=True)
#         reporter.write_line('Retrieved these appliances from the --sprout-* parameters', red=True)
#
#         holder = config.pluginmanager.getplugin('appliance-holder')
#
#         for appliance in appliances:
#             reporter.write_line('* {!r}'.format(appliance), cyan=True)
#
#         holder.stack.push(appliances[0])
#         holder.held_appliance = appliances[0]
#         holder.pool = appliances
#
#
# @pytest.hookimpl(trylast=True)
# def pytest_unconfigure(config):
#     app_type = config.getoption('--app-type')
#     if APP_TYPE == app_type:
#         holder = config.pluginmanager.getplugin('appliance-holder')
#         holder.stack.pop()
#
#
# @attr.s(eq=False)
# class LocalAppliancePlugin(object):
#     pass
