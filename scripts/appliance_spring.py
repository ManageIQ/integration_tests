from utils import appliance
from utils import providers
from utils import conf
import threading
import datetime
import time
from utils import pretty


class Vm(pretty.Pretty):
    pretty_attrs = ["name", "provider_name", "template_name"]

    def __init__(self, name, provider_name, template_name):
        self.name = name
        self.provider_name = provider_name
        self.template_name = template_name


def vm_generator(provider_name, template_name):
    '''Generates unique Vm definitions using the given template
    name and provider name'''
    d = datetime.datetime.now()
    offset = 0
    while True:
        next_d = d + datetime.timedelta(0, offset)  # 1 sec later datestamp
        datestamp = next_d.isoformat()
        offset += 1
        yield Vm("appspring-{}-{}".format(template_name, datestamp),
                 provider_name, template_name)


def deploy(vm):
    provider = providers.provider_factory(vm.provider_name)
    provider.deploy_template(vm.template_name, vm.name)


def init():
    conf.clear()


def queue_filter(template_name):
    return lambda vm_name: vm_name.startswith("appspring-{}".format(template_name))


def wait_for_queue_space(max_size, vmdef):
    provider = providers.provider_factory(vmdef.provider_name)
    q_filter = queue_filter(vmdef.template_name)
    while True:
        if len(filter(q_filter, provider.list_vm())) < max_size:
            break
        else:
            print("Queue for template {} is full".format(vmdef.template_name))
            time.sleep(120)


def start_queue(provider_name, template_name, max_size=2):
    def manage_queue():
        for vmdef in vm_generator(provider_name, template_name):
            wait_for_queue_space(max_size, provider_name, template_name)
            print("Deploying {}".format(vmdef))
            deploy(vmdef)
    threading.Thread(target=manage_queue).start()
