""" Base module for Management Systems classes. """

from abc import ABCMeta, abstractmethod
from pysphere import *
from pysphere.resources.vi_exception import VIException
from pysphere.resources import VimService_services as VI
from pysphere.vi_task import VITask
from ovirtsdk.api import API

class MgmtSystemAPIBase(object):
    """ Base interface class for Management Systems. """
    __metaclass__ = ABCMeta

    @abstractmethod
    def start_vm(self, vm_name):
        '''
            Starts a vm.

            :param vm_name: name of the vm to be started
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        '''
        raise NotImplementedError('start_vm not implemented.')

    @abstractmethod
    def stop_vm(self, vm_name):
        '''
            Stops a vm.

            :param vm_name: name of the vm to be stopped
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        '''
        raise NotImplementedError('stop_vm not implemented.')

    @abstractmethod
    def create_vm(self, vm_name):
        '''
            Creates a vm.

            :param vm_name: name of the vm to be created
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        '''
        raise NotImplementedError('create_vm not implemented.')

    @abstractmethod
    def delete_vm(self, vm_name):
        '''
            Deletes a vm.

            :param vm_name: name of the vm to be deleted
            :type  vm_name: str
            :return: whether vm action has been initiated properly
            :rtype: boolean
        '''
        raise NotImplementedError('delete_vm not implemented.')

    @abstractmethod
    def restart_vm(self, vm_name):
        '''
            Restart a vm.

            :param vm_name: name of the vm to be restarted
            :type  vm_name: str
            :return: whether vm stop/start have been initiated properly
            :rtype: boolean
        '''
        raise NotImplementedError('restart_vm not implemented.')

    @abstractmethod
    def list_vm(self, **kwargs):
        '''
            Returns a list of vm names.

            :return: list of vm names
            :rtype: list
        '''
        raise NotImplementedError('list_vm not implemented.')

    @abstractmethod
    def info(self):
        '''
            Returns basic information about the mgmt system.

            :return: string representation of name/version of mgmt system.
            :rtype: str
        '''
        raise NotImplementedError('info not implemented.')

    @abstractmethod
    def disconnect(self):
        '''
            Disconnect the API from mgmt system.
        '''
        raise NotImplementedError('disconnect not implemented.')

    @abstractmethod
    def vm_status(self, vm_name):
        '''
            Status of VM.

            :param vm_name: name of the vm to get status 
            :type  vm_name: str
            :return: state of the vm
            :rtype: string
        '''
        raise NotImplementedError('vm_status not implemented.')

    @abstractmethod
    def is_vm_running(self, vm_name):
        '''
            Is the vm running?

            :param vm_name: name of the vm
            :type  vm_name: str
            :return: whether the vm is running or not 
            :rtype: boolean
        '''
        raise NotImplementedError('is_vm_running not implemented.')

    @abstractmethod
    def is_vm_stopped(self, vm_name):
        '''
            Is the vm stopped?

            :param vm_name: name of the vm 
            :type  vm_name: str
            :return: whether the vm is stopped or not 
            :rtype: boolean
        '''
        raise NotImplementedError('is_vm_stopped not implemented.')

    @abstractmethod
    def is_vm_suspended(self, vm_name):
        '''
            Is the vm suspended?

            :param vm_name: name of the vm 
            :type  vm_name: str
            :return: whether the vm is suspended or not 
            :rtype: boolean
        '''
        raise NotImplementedError('is_vm_suspended not implemented.')

    @abstractmethod
    def suspend_vm(self, vm_name):
        '''
            Suspend a vm.

            :param vm_name: name of the vm to be suspended
            :type  vm_name: str
            :return: whether vm suspend has been initiated properly
            :rtype: boolean
        '''
        raise NotImplementedError('restart_vm not implemented.')


class VMWareSystem(MgmtSystemAPIBase):
    """
    Client to Vsphere API

    This class piggy backs off pysphere.

    Benefits of pysphere:
      - Don't need intimate knowledge w/ vsphere api itself.
    Detriments of pysphere:
      - Response often are not detailed enough. 
    """
    def __init__(self, hostname='localhost', username='root', password='rootpwd'):
        """ Initialize VMWareSystem """     
        # sanitize hostname
        if hostname.startswith('https://'):
            hostname.replace('https://', '')
        elif hostname.startswith('http://'):
            hostname.replace('http://', '')

        if hostname.endswith('/api'):
            hostname.replace('/api', '')

        self.api = VIServer()
        self.api.connect(hostname, username, password)

    def _get_vm(self, vm_name=None):
        """ RHEVMSystem implementation in _get_vm. """
        if vm_name is None:
            raise Exception('Could not find a VM named %s.' % vm_name)
        else:
            try:
                vm = self.api.get_vm_by_name(vm_name)
                return vm
            except VIException as ex:
                raise Exception(ex)

    def start_vm(self, vm_name):
        """ VMWareSystem implementation of start_vm. """
        vm = self._get_vm(vm_name)
        if vm.is_powered_on():
            raise Exception('Could not start %s because it\'s already running.' % vm_name)
        else:
            vm.power_on()
            ack = vm.get_status()
            if ack == 'POWERED ON':
                return True
        return False

    def stop_vm(self, vm_name):
        """ VMWareSystem implementation of stop_vm. """
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            raise Exception('Could not stop %s because it\'s not running.' % vm_name)
        else:
            vm.power_off()
            ack = vm.get_status()
            if ack == 'POWERED OFF':
                return True
        return False

    def delete_vm(self, vm_name):
        """ VMWareSystem implementation of delete_vm. """
        vm = self._get_vm(vm_name)

        if vm.is_powered_on():
            raise Exception('Could not stop %s because it\'s still running.' % vm_name)
        else:
            # When pysphere moves up to 0.1.8, we can just do:
            # vm.destroy()
            request = VI.Destroy_TaskRequestMsg()
            _this = request.new__this(vm._mor)
            _this.set_attribute_type(vm._mor.get_attribute_type())
            request.set_element__this(_this)
            rtn = self.api._proxy.Destroy_Task(request)._returnval

            task = VITask(rtn, self.api)
            status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR])
            if status == task.STATE_SUCCESS:
                return True
        return False

    def create_vm(self, vm_name):
        """ VMWareSystem implementation of create_vm. """
        #Unfortunately, there are not enough smurf slaves in the village to build this functionality yet. 
        pass

    def restart_vm(self, vm_name):
        """ VMWareSystem implementation of restart_vm. """
        if not self.stop_vm(vm_name):
            return False
        else:
            return self.start_vm(vm_name)

    def list_vm(self, **kwargs):
        """ VMWareSystem implementation of list_vm. """
        vm_list = self.api.get_registered_vms(**kwargs)
        return [vm.split(']', 1)[-1].strip() for vm in vm_list]

    def info(self):
        """ VMWareSystem implementation of info. """
        return '%s %s' % (self.api.get_server_type(), self.api.get_api_version())

    def disconnect(self):
        """ VMWareSystem implementation of disconnect. """
        self.api.disconnect()

    def vm_status(self, vm_name):
        """ VMWareSystem implementation of vm.get_status """
        state = self._get_vm(vm_name).get_status()
        print "vm " + vm_name + " status is " + state 
        return state

    def is_vm_running(self, vm_name):
        """ VMWareSystem implementation of is_vm_running. """
        state = self.vm_status(vm_name)
        return "POWERED ON" == state

    def is_vm_stopped(self, vm_name):
        """ VMWareSystem implementation of is_vm_stopped. """
        state = self.vm_status(vm_name)
        return "POWERED OFF" == state

    def is_vm_suspended(self, vm_name):
        """ VMWareSystem implementation of is_vm_suspended. """
        state = self.vm_status(vm_name)
        return "SUSPENDED" == state

    def suspend_vm(self, vm_name):
        """ VMWareSystem implementation of suspend_vm. """
        vm = self._get_vm(vm_name)
        if vm.is_powered_off():
            raise Exception('Could not suspend %s because it\'s not running.' % vm_name)
        else:
            vm.suspend()
            return vm.get_status()
        return False


class RHEVMSystem(MgmtSystemAPIBase):
    """
    Client to RHEVM API

    This class piggy backs off ovirtsdk.

    Benefits of ovirtsdk: 
    - Don't need intimite knowledge w/ RHEVM api itself. 
    Detriments of ovirtsdk:
    - Response to most quaries are returned as an object rather than a string. 
      This makes it harder to do simple stuff like getting the status of a vm.
    - Because of this, it makes listing VMs based on **kwargs impossible 
      since ovirtsdk relies on re class to find matches. 

    I.E. List out VM with this name (positive case)
      Ideal: self.api.vms.list(name='test_vm')
      Underneath the hood: 
        - ovirtsdk fetches list of all vms [ovirtsdk.infrastructure.brokers.VM object, ...]
        - ovirtsdk then tries to filter the result using re.
          - tries to look for 'name' attr in ovirtsdk.infrastructure.brokers.VM object
          - found name attribute, in this case, the type of the value of the attribute is string.
          - match() succeed in comparing the value to 'test_vm'

    I.E. List out VM with that's powered on (negative case)
      Ideal: self.api.vms.list(status='up')
      Underneath the hood: 
        - '^same step as above except^'
            - found status attribute, in this case, the type of the value of the attribute is .
virtsdk.xml.params.Status
            - match() failed because class is compared to string 'up'

     This problem should be attributed to how RHEVM api was designed rather than how ovirtsdk handles RHEVM api responses. 

    - Obj. are not updated after action calls.
      - I.E. 
        vm = api.vms.get(name='test_vm')
        vm.status.get_state() # returns 'down'
        vm.start()
        # wait a few mins
        vm.status.get_state() # returns 'down'; wtf?

        vm = api.vms.get(name='test_vm')
        vm.status.get_state() # returns 'up'
    """
    def __init__(self, hostname='localhost', username='root', password='rootpwd'):
        """ Initialize RHEVMSystem """     
        # sanitize hostname
        if not hostname.startswith('https://'):
            hostname = 'https://%s' % hostname
        if not hostname.endswith('/api'):
            hostname = '%s/api' % hostname

        self.api = API(url=hostname, username=username, password=password, insecure=True)

    def _get_vm(self, vm_name=None):
        """ RHEVMSystem implementation in _get_vm. """
        if vm_name is None:
            raise Exception('Could not find a VM named %s.' % vm_name)
        else:
            vm = self.api.vms.get(name=vm_name)
            if vm is None:
                raise Exception('Could not find a VM named %s.' % vm_name)
            return vm

    def start_vm(self, vm_name=None):
        """ RHEVMSystem implementation of start_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            raise Exception('Could not start %s because it\'s already running.' % vm_name)
        else:
            ack = vm.start()
            if ack.get_status().get_state() == 'complete':
                return True
        return False

    def stop_vm(self, vm_name):
        """ RHEVMSystem implementation of stop_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise Exception('Could not stop %s because it\'s not running.' % vm_name)
        else:
            ack = vm.stop()
            if ack.get_status().get_state() == 'complete':
                return True
        return False

    def delete_vm(self, vm_name):
        """ RHEVMSystem implementation of delete_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'up':
            raise Exception('Could not delete %s because it\'s still running.' % vm_name)
        else:
            ack = vm.delete()
            if ack.get_status().get_state() == '':
                return True
        return False

    def create_vm(self, vm_name):
        """ RHEVMSystem implementation of create_vm. """
        #Unfortunately, there are not enough smurf slaves in the village to build this functionality yet. 
        pass

    def restart_vm(self, vm_name):
        """ RHEVMSystem implementation of restart_vm. """
        if not self.stop_vm(vm_name):
            return False
        else:
            return self.start_vm(vm_name)

    def list_vm(self, **kwargs):
        """ RHEVMSystem implementation of list_vm. """
        # list vm based on kwargs can be buggy
        # i.e. you can't return a list of powered on vm
        # but you can return a vm w/ a matched name
        vm_list = self.api.vms.list(**kwargs)
        return [vm.name for vm in vm_list]

    def info(self):
        """ RHEVMSystem implementation of info. """
        # and we got nothing!
        pass

    def disconnect(self):
        """ RHEVMSystem implementation of disconnect. """
        self.api.disconnect()

    def vm_status(self, vm_name=None):
        """ RHEVMSystem implementation of vm_status. """
        state = self._get_vm(vm_name).get_status().get_state()
        print "vm " + vm_name + " status is " + state 
        return state

    def is_vm_running(self, vm_name):
        """ RHEVMSystem implementation of is_vm_running. """
        state = self.vm_status(vm_name)
        return "up" == state

    def is_vm_stopped(self, vm_name):
        """ RHEVMSystem implementation of is_vm_stopped. """
        state = self.vm_status(vm_name)
        return "down" == state

    def is_vm_suspended(self, vm_name):
        """ RHEVMSystem implementation of is_vm_suspended. """
        state = self.vm_status(vm_name)
        return "suspended" == state

    def suspend_vm(self, vm_name):
        """ RHEVMSystem implementation of suspend_vm. """
        vm = self._get_vm(vm_name)
        if vm.status.get_state() == 'down':
            raise Exception('Could not suspend %s because it\'s not running.' % vm_name)
        else:
            ack = vm.suspend()
            return ack.get_status().get_state() == 'complete'
        return False

