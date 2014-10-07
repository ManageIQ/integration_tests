#from utils import appliance
from utils import providers
from utils import conf
import threading
import datetime
import time
from utils import pretty


class Queue(pretty.Pretty):
    pretty_attrs = ["provider_name", "template_name"]

    def __init__(self, provider_name, template_name, max_size=2):
        self.provider_name = provider_name
        self.template_name = template_name
        self.max_size = max_size
        self.shutdown_flag = False
        self.provider = providers.provider_factory(self.provider_name)

    def vm_generator(self):
        '''Generates unique Vm definitions for this queue'''
        d = datetime.datetime.now()
        offset = 0
        while True:
            next_d = d + datetime.timedelta(0, offset)  # 1 sec later datestamp
            datestamp = next_d.isoformat()
            offset += 1
            yield Vm("appspring-{}-{}".format(self.template_name, datestamp), self)

    def _filter(self, vm_name):
        return vm_name.startswith("appspring-{}".format(self.template_name))

    def running_vms(self):
        '''Returns a list of names of running vms in this queue'''
        return filter(self._filter, self.provider.list_vm())

    def wait_for_space(self):
        while True:
            if len(self.running_vms()) < self.max_size:
                break
            else:
                print("Queue for template {} is full".format(self.template_name))
                time.sleep(120)

    def start(self):
        def manage():
            for vmdef in self.vm_generator():
                if self.shutdown_flag:
                    self.shutdown()
                    break
                wait_for_space()
                print("Deploying {}".format(vmdef))
                vmdef.deploy()
        threading.Thread(target=manage).start()

    def shutdown(self):
        for vm in self.running_vms():
            vm.delete()


class Vm(pretty.Pretty):
    pretty_attrs = ["name", "queue"]

    def __init__(self, name, queue):
        self.name = name
        self.queue = queue

    def deploy():
        self.queue.provider.deploy_template(self.queue.template_name,
                                            vm_name=self.name)

    def delete():
        self.queue.provider.delete_vm(self.name)


def init():
    conf.clear()




# TODO just keep one copy of the last vm list for all threads,
# to avoid hammering the providers with refreshes


def manage_all_queues():
    # in the main thread, scan the templates for names "autoqueue-*",
    # so the individual queues can see when they've been decommissioned,
    # and shut down their queues'
    pass
