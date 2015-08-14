#!/usr/bin/env python2
from utils import providers
from utils import conf
import threading
import datetime
import time
from utils import pretty
import re
import sys
import argparse

# don't allow template names to specify any queue larger than this
queue_size_guard = 10


class Queue(pretty.Pretty):
    pretty_attrs = ["provider_name", "template_name"]

    def __init__(self, provider_name, template_name, max_size=2):
        self.provider_name = provider_name
        self.template_name = template_name
        self.max_size = max_size
        self.shutdown_flag = False
        self.provider = providers.get_mgmt(self.provider_name)

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

    def current_size(self):
        while True:
            try:
                queue_size = len(self.running_vms())
            except Exception:
                queue_size = self.max_size
            return queue_size

    def start(self):
        '''starts managing this queue in a new thread'''
        def manage():
            print("Now managing {}".format(self))
            vms = self.vm_generator()
            while not self.shutdown_flag:
                queue_size = self.current_size()
                if queue_size < self.max_size:
                    # there's space, fill it
                    for _ in range(self.max_size - queue_size):
                        vm = vms.next()
                        threading.Thread(target=vm.deploy, name=vm.name + " deploy").start()
                    time.sleep(90)  # wait for them to be deployed so we dont overshoot
                elif queue_size > self.max_size:
                    # we overshot, go back, go back!
                    print("Queue for template {} is over-full, shrinking...".format(
                        self.template_name))
                    for vm_name in self.running_vms()[self.max_size - 1:]:  # all beyond max_size
                        Vm(vm_name, self).delete()
                else:
                    print("Queue for template {} is full".format(self.template_name))
                time.sleep(45)

            self._stop()

        threading.Thread(target=manage, name="{} on {}".format(
            self.template_name, self.provider_name)).start()

    def _stop(self):
        print("No longer managing queue {} - shutting down".format(self))
        for vm in self.running_vms():
            self.provider.delete_vm(vm)

    def stop(self):
        '''Tells the queue to stop and remove all remaining vms'''
        print("Stopping queue: {}".format(self))
        self.shutdown_flag = True


class Vm(pretty.Pretty):
    pretty_attrs = ["name", "queue"]

    def __init__(self, name, queue):
        self.name = name
        self.queue = queue

    def deploy(self):
        print("Deploying: {}".format(self.name))
        self.queue.provider.deploy_template(self.queue.template_name,
                                            vm_name=self.name)

    def delete(self):
        print("Deleting: {}".format(self.name))
        self.queue.provider.delete_vm(self.name)


def init():
    conf.clear()

# TODO just keep one copy of the last vm list for all threads,
# to avoid hammering the providers with refreshes


def _template_provider_filter(provider_name, template_name):
    return lambda q: q.template_name == template_name and q.template_name == template_name


def _is_in_queue_set(qset, provider_name, template_name):
    return len(filter(_template_provider_filter(provider_name, template_name), qset)) > 0


queues = set()


def manage_all_queues(target_providers):
    '''Scan the templates of given providers for templates named
    "autoqueue-nn-*".  Create nn vms that are ready to be consumed.

    If such a template disappears (or is renamed) its queue will be no
    longer be managed. The vms in it will remain but no new ones will
    be created.

    No distinction is made between vms that are stopped or running.
    If someone stops a vm in the queue, it will remain in the queue.

    To take a vm from the queue, rename it so that it no longer has a
    prefix "appspring-".

    The vm becomes your responsibility to manage - destroy it when
    you're finished with it.

    '''
    init()
    provs = {(p, providers.get_mgmt(p)) for p in target_providers}
    global queues
    queues = set()
    template_re = re.compile("autoqueue-(\d+)")
    while True:
        for provider_name, provider in provs:
            try:
                templates = filter(lambda t: template_re.match(t), provider.list_template())
                for template_name in templates:
                    if not _is_in_queue_set(queues, provider_name, template_name):
                        max_size = int(template_re.match(template_name).group(1))
                        q = Queue(provider_name, template_name,
                                  max_size=min(max_size, queue_size_guard))
                        queues.add(q)
                        q.start()
                for q in queues:
                    if q.template_name not in templates and q.provider_name == provider_name:
                        q.stop()
                queues = set(filter(lambda q: not q.shutdown_flag, queues))
            except BaseException as be:
                print("Could not process queue for provider {}: {}".format(provider_name, be))
        time.sleep(45)


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('providers', help='space-separated list of providers to be managed',
                        nargs='*')

    args = parser.parse_args()
    manage_all_queues(args.providers)


if __name__ == '__main__':
    sys.exit(main())
