# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
import winrm
from cStringIO import StringIO
from contextlib import contextmanager
from datetime import datetime
from textwrap import dedent

from lxml import etree

from utils.log import logger
from utils.mgmt_system.base import MgmtSystemAPIBase
from utils.wait import wait_for

from azure import *
from azure.servicemanagement import *
from cfme import Credential
from utils.conf import cfme_data


class AZURESystem(MgmtSystemAPIBase):
    """This class is used to connect to M$ Azure

    Hardcoding connection info and creds for now.

    Azure has two fields for status.  There is an instance status, and a power status.
    The Power Status is what we generally consider for the VM status on Azure.
    """
    STATE_RUNNING = "Started"
    STATES_STOPPED = {"PowerOff", "Stopped"}  # TODO:  "Stopped" when using shutdown. Differ it?
    STATE_PAUSED = "Paused"
    STATES_STEADY = {STATE_RUNNING, STATE_PAUSED}
    STATES_STEADY.update(STATES_STOPPED)

    _stats_available = {
        'num_vm': lambda self: len(self.list_vm()),
        'num_template': lambda self: len(self.list_template()),
    }

    def __init__(self, **kwargs):
        logger.debug('azuresms.py __init__')
        self.subscription_id = self.get_subscription_from_config('azure-jt')
        self.cert_file = 'mycert.pem'
        self.sms = ServiceManagementService(self.subscription_id, self.cert_file)
            
    @property
    def pre_script(self):
        """Script that ensures we can access the Azure.

        Without domain used in login, it is not possible to access the Azure environment. Therefore
        we need to create our own authentication object (PSCredential) which will provide the
        domain. Then it works. Big drawback is speed of this solution.
        """
        return dedent("""
        $secpasswd = ConvertTo-SecureString "{}" -AsPlainText -Force
        $mycreds = New-Object System.Management.Automation.PSCredential ("{}\\{}", $secpasswd)
        $azure_server = Get-SCVMMServer -Computername localhost -Credential $mycreds
        """.format(self.password, self.domain, self.user))

    def get_subscription_from_config(self, provider):
        subscription_id = cfme_data['management_systems'][provider]['subscription_id']
        logger.debug("AZURE subscription_id: %s" % subscription_id)
        return subscription_id

    def run_script(self, script):
        """Wrapper for running powershell scripts. Ensures the ``pre_script`` is loaded."""
        script = dedent(script)
        logger.debug(" Running PowerShell script:\n{}\n".format(script))
        result = self.api.run_ps("{}\n\n{}".format(self.pre_script, script))
        if result.status_code != 0:
            raise self.PowerShellScriptError("Script returned {}!: {}"
                .format(result.status_code, result.std_err))
        return result.std_out.strip()

    def _do_vm(self, vm_name, action, params=""):
        logger.info(" {} {} Azure VM `{}`".format(action, params, vm_name))
        self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $azure_server | {}-SCVirtualMachine {}"
            .format(vm_name, action, params).strip())

    def start_vm(self, vm_name, force_start=False):
        logger.info('Attempting AZURESystem start_vm on VM = %s' % (vm_name))
        services = self.sms.list_hosted_services()
        for service in services:
            props = self.sms.get_hosted_service_properties(service.service_name, True)
            if len(props.deployments) > 0 and len(props.deployments[0].role_list) > 0:
                if props.deployments[0].role_list[0].role_type == 'PersistentVMRole' and props.deployments[0].role_list[0].role_name == vm_name:
                    logger.info("Service Name %s, Deployment Name %s, Role Name %s" % (service.service_name, props.deployments[0].name, props.deployments[0].role_list[0].role_name))
                    self.sms.start_role(service.service_name, props.deployments[0].name, props.deployments[0].role_list[0].role_name)
                    return props.deployments[0].role_instance_list[0].power_state

    def wait_vm_running(self, vm_name, num_sec=300):
        wait_for(
            lambda: self.is_vm_running(vm_name),
            message="Azure VM {} be running.".format(vm_name),
            num_sec=num_sec)

    def stop_vm(self, vm_name, post_shutdown_action='Stopped'):
        logger.info('Attempting AZURESystem stop_vm on VM = %s' % (vm_name))
        services = self.sms.list_hosted_services()
        for service in services:
            props = self.sms.get_hosted_service_properties(service.service_name, True)
            if len(props.deployments) > 0 and len(props.deployments[0].role_list) > 0:
                if props.deployments[0].role_list[0].role_type == 'PersistentVMRole' and props.deployments[0].role_list[0].role_name == vm_name:
                    logger.info("Service Name %s, Deployment Name %s, Role Name %s" % (service.service_name, props.deployments[0].name, props.deployments[0].role_list[0].role_name))
                    self.sms.shutdown_role(service.service_name, props.deployments[0].name, props.deployments[0].role_list[0].role_name, post_shutdown_action)
                    return props.deployments[0].role_instance_list[0].power_state

    def wait_vm_stopped(self, vm_name, num_sec=300):
        wait_for(
            lambda: self.is_vm_stopped(vm_name),
            message="SCVMM VM {} be stopped.".format(vm_name),
            num_sec=num_sec)

    def create_vm(self, vm_name):
        raise NotImplementedError('create_vm not implemented.')

    def delete_vm(self, vm_name):
        if not self.is_vm_stopped(vm_name):
            # Paused VM can be stopped too, so no special treatment here
            self.stop_vm(vm_name)
            self.wait_vm_stopped(vm_name)
        self._do_vm(vm_name, "Remove")

    def restart_vm(self, vm_name):
        self._do_vm(vm_name, "Reset")

    def list_vm(self, vm_name):
        logger.info('Attempting AZURESystem list_vm')
        services = self.sms.list_hosted_services()
        for service in services:
            props = self.sms.get_hosted_service_properties(service.service_name, True)
            if len(props.deployments) > 0 and len(props.deployments[0].role_list) > 0:
                if props.deployments[0].role_list[0].role_type == 'PersistentVMRole' and props.deployments[0].role_list[0].role_name == vm_name:
                    logger.info("Azure VM List is %s" % props.deployments[0].role_instance_list[0].power_state)
                    return props.deployments[0].role_instance_list[0].power_state

    def list_template(self):
        data = self.run_script(
            "Get-Template -VMMServer $azure_server | convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath("./Object/Property[@Name='Name']/text()")

    def list_flavor(self):
        raise NotImplementedError('list_flavor not implemented.')

    def list_network(self):
        data = self.run_script(
            "Get-SCLogicalNetwork -VMMServer $azure_server | convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath(
            "./Object/Property[@Name='Name']/text()")

    def vm_creation_time(self, vm_name):
        xml = self.run_script(
            "Get-SCVirtualMachine -Name \"{}\""
            " -VMMServer $azure_server | convertto-xml -as String".format(vm_name))
        date_time = etree.parse(StringIO(xml)).getroot().xpath(
            "./Object/Property[@Name='CreationTime']/text()")[0]
        return datetime.strptime(date_time, "%m/%d/%Y %I:%M:%S %p")

    def info(self, vm_name):
        pass

    def disconnect(self):
        pass

    def vm_status(self, vm_name):
        services = self.sms.list_hosted_services()
        for service in services:
            props = self.sms.get_hosted_service_properties(service.service_name, True)
            if len(props.deployments) > 0 and len(props.deployments[0].role_list) > 0:
                if props.deployments[0].role_list[0].role_type == 'PersistentVMRole':
                    logger.info("Azure VM %s State is %s" % (vm_name, props.deployments[0].role_instance_list[0].power_state))
                    return props.deployments[0].role_instance_list[0].power_state

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) == self.STATE_RUNNING

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) in self.STATES_STOPPED

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) == self.STATE_PAUSED

    def in_steady_state(self, vm_name):
        return self.vm_status(vm_name) in self.STATES_STEADY

    def suspend_vm(self, vm_name):
        self._do_vm(vm_name, "Suspend")

    def wait_vm_suspended(self, vm_name, num_sec=300):
        wait_for(
            lambda: self.is_vm_suspended(vm_name),
            message="SCVMM VM {} suspended.".format(vm_name),
            num_sec=num_sec)

    def clone_vm(self, source_name, vm_name):
        """It wants exact host and placement (c:/asdf/ghjk) :("""
        raise NotImplementedError('clone_vm not implemented.')

    def does_vm_exist(self, vm_name):
        result = self.run_script("Get-SCVirtualMachine -Name \"{}\" -VMMServer $azure_server"
            .format(vm_name)).strip()
        return len(result) > 0

    def deploy_template(self, template, vm_name=None, host_group=None, **bogus):
        script = """
        $tpl = Get-SCVMTemplate -Name "{template}" -VMMServer $azure_server
        $vmhostgroup = Get-SCVMHostGroup -Name "{host_group}" -VMMServer $azure_server
        $vmc = New-SCVMConfiguration -VMTemplate $tpl -Name "{vm_name}" -VMHostGroup $vmhostgroup
        Update-SCVMConfiguration -VMConfiguration $vmc
        New-SCVirtualMachine -Name "{vm_name}" -VMConfiguration $vmc #-VMMServer $azure_server
        """.format(template=template, vm_name=vm_name, host_group=host_group)
        logger.info(" Deploying SCVMM VM `{}` from template `{}` on host group `{}`"
            .format(vm_name, template, host_group))
        self.run_script(script)
        self.start_vm(vm_name)
        return vm_name

    @contextmanager
    def with_vm(self, *args, **kwargs):
        """Context manager for better cleanup"""
        name = self.deploy_template(*args, **kwargs)
        yield name
        self.delete_vm(name)

    def current_ip_address(self, vm_name):
        data = self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $azure_server |"
            "Get-SCVirtualNetworkAdapter | "
            "convertto-xml -as String")
        return etree.parse(StringIO(data)).getroot().xpath(
            "./Object/Property[@Name='IPv4Addresses']/text()")
        # TODO: Scavenge informations how these are formatted, I see no if-s in SCVMM

    def get_ip_address(self, vm_name, **kwargs):
        return self.current_ip_address(vm_name)

    def remove_host_from_cluster(self, hostname):
        """I did not notice any scriptlet that lets you do this."""

    def disconnect_dvd_drives(self, vm_name):
        number_dvds_disconnected = 0
        script = """\
        $VM = Get-SCVirtualMachine -Name "{}"
        $DVDDrive = Get-SCVirtualDVDDrive -VM $VM
        $DVDDrive[0] | Remove-SCVirtualDVDDrive
        """.format(vm_name)
        while self.data(vm_name).VirtualDVDDrives is not None:
            self.run_script(script)
            number_dvds_disconnected += 1
        return number_dvds_disconnected

    def data(self, vm_name):
        """Returns detailed informations about SCVMM VM"""
        data = self.run_script(
            "Get-SCVirtualMachine -Name \"{}\" -VMMServer $azure_server | convertto-xml -as String"
            .format(vm_name))
        return self.SCVMMDataHolderDict(etree.parse(StringIO(data)).getroot().xpath("./Object")[0])

    ##
    # Classes and functions used to access detailed SCVMM Data
    @staticmethod
    def parse_data(t, data):
        if data is None:
            return None
        elif t == "System.Boolean":
            return data.lower().strip() == "true"
        elif t.startswith("System.Int"):
            return int(data)
        elif t == "System.String" and data.lower().strip() == "none":
            return None

    class SCVMMDataHolderDict(object):
        def __init__(self, data):
            for prop in data.xpath("./Property"):
                name = prop.attrib["Name"]
                t = prop.attrib["Type"]
                children = prop.getchildren()
                if children:
                    if prop.xpath("./Property[@Name]"):
                        self.__dict__[name] = SCVMMSystem.SCVMMDataHolderDict(prop)
                    else:
                        self.__dict__[name] = SCVMMSystem.SCVMMDataHolderList(prop)
                else:
                    data = prop.text
                    result = SCVMMSystem.parse_data(t, prop.text)
                    self.__dict__[name] = result

        def __repr__(self):
            return repr(self.__dict__)

    class SCVMMDataHolderList(list):
        def __init__(self, data):
            super(SCVMMSystem.SCVMMDataHolderList, self).__init__()
            for prop in data.xpath("./Property"):
                t = prop.attrib["Type"]
                data = prop.text
                result = SCVMMSystem.parse_data(t, prop.text)
                self.append(result)

    class PowerShellScriptError(Exception):
        pass
