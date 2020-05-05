import cfme.utils.conf as conf
from cfme.fixtures import terminalreporter
from cfme.utils.appliance import load_appliances_from_config
reporter = terminalreporter.reporter()

appliances = load_appliances_from_config(conf.env)
reporter.write_line('Retrieved these appliances from the conf.env', red=True)

# TODO: decide how we can handle this
