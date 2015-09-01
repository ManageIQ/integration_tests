#!/usr/bin/env python2

from utils.conf import rhci
from utils.providers import get_mgmt

mgmt = get_mgmt(rhci.provider_key)
for vm_name in rhci.vm_names:
    try:
        print "Deleting {} on {}".format(vm_name, rhci.provider_key)
        mgmt.delete_vm(vm_name)
        print "Done"
    except:
        # If the VM doesn't exist when deleting, that's...weird...but okay?
        print "{} does not exist or can't be deleted.".format(vm_name)
