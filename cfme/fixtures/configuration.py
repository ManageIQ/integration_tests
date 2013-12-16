import yaml
import py.path
# save off the config options in a globally accessible place


def load_config(filename=None):
    path = py.path.local(filename)
    if path.check():
        config_fh = path.open()
        config_dict = yaml.load(config_fh)
        return config_dict
    else:
        msg = 'Unable to load configuration file at %s' % path
        raise Exception(msg)


conf = {}


def get():
    return conf


def get_in(*keys):
    dct = conf
    for k in keys:
        next = dct.get(k)
        if next:
            dct = next
        else:
            return None
    return dct


default_config_file = "./conf/config.yaml"


def init(filename=default_config_file):
    global conf
    conf = load_config(filename)


def pytest_configure(config):
    init()

    
