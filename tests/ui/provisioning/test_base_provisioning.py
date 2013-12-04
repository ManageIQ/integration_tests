# -*- coding: utf-8 -*-
# pylint: disable=W0621
from unittestzero import Assert
import db


class TestBaseProvisioning:
    def complete_provision_pages_info(
            self,
            provisioning_data, provision_pg, random_name):
        ''' Fills in data for Provisioning tabs'''
        tab_buttons = provision_pg.tabbutton_region
        request_pg = tab_buttons.tabbutton_by_name("Request").click()
        self.complete_request_page(request_pg)

        purpose_pg = tab_buttons.tabbutton_by_name("Purpose").click()
        self.complete_purpose_pg(purpose_pg, provisioning_data)

        catalog_pg = tab_buttons.tabbutton_by_name("Catalog").click()
        self.complete_catalog_pg(catalog_pg, provisioning_data, random_name)

        environment_pg = tab_buttons.tabbutton_by_name("Environment").click()
        self.complete_environment_pg(environment_pg, provisioning_data)

        if "instance_type" in provisioning_data:
            properties_pg = tab_buttons.tabbutton_by_name("Properties").click()
            self.complete_properties_pg(properties_pg, provisioning_data)
        else:
            tab_buttons.tabbutton_by_name("Hardware").click()
            tab_buttons.tabbutton_by_name("Network").click()

        if provisioning_data["provision_type"] is not None:
            if ("PXE" in provisioning_data["provision_type"]) or \
                    ("ISO" in provisioning_data["provision_type"]):
                customize_pg = tab_buttons.tabbutton_by_name("Customize").click()
                self.complete_customize_pg(customize_pg, provisioning_data)

        schedule_pg = tab_buttons.tabbutton_by_name("Schedule").click()
        self.complete_schedule_pg(schedule_pg, provisioning_data)

        services_requests_pg = schedule_pg.click_on_submit()
        self.complete_services_requests_pg(services_requests_pg)

    def complete_request_page(self, request_pg):
        '''Completes fields in Request tab'''
        request_pg.fill_fields(
            "admin@example.com",
            "admin",
            "admin",
            "Adding a test note",
            "Manager Name")

    def complete_purpose_pg(self, purpose_pg, provisioning_data):
        '''Purpose tab fields'''
        # tree = purpose_pg.click_on_nodes(provisioning_data["node"],
        # provisioning_data["child_node")

    def complete_catalog_pg(self, catalog_pg, provisioning_data, random_name):
        '''Catalog tab fields'''
        catalog_pg.fill_fields(
            provisioning_data["provision_type"],
            provisioning_data["pxe_server"],
            provisioning_data["server_image"],
            str(provisioning_data["count"]),
            '%s%s' % (provisioning_data["vm_name"], random_name),
            provisioning_data["vm_description"])

    def complete_environment_pg(self, environment_pg, provisioning_data):
        '''Environment tab fields'''
        if "availability_zone" in provisioning_data:
            environment_pg.fill_fields_cloud(
                provisioning_data["availability_zone"],
                provisioning_data["security_group"],
                provisioning_data["public_ip_address"])
        else:
            environment_pg.fill_fields_infra(
                unicode(provisioning_data["host"]),
                unicode(provisioning_data["datastore"]))

    def complete_properties_pg(self, properties_pg, provisioning_data):
        '''Properties tab fileds'''
        properties_pg.fill_fields(
            provisioning_data["instance_type"],
            provisioning_data["key_pair"])

    def complete_customize_pg(self, customize_pg, provisioning_data):
        '''Customize tab fields'''
        customize_pg.fill_fields(
            provisioning_data["root_password"],
            provisioning_data["address_node_value"],
            provisioning_data["customization_template"])

    def complete_schedule_pg(self, schedule_pg, provisioning_data):
        '''Schedule tab fields'''
        schedule_pg.fill_fields(
            provisioning_data["when_to_provision"],
            provisioning_data["power_on"],
            str(provisioning_data["time_until_retirement"]))

    def complete_services_requests_pg(self, services_requests_pg):
        '''Complete services request'''
        Assert.true(
            services_requests_pg.is_the_current_page,
            "not returned to the correct page")
        Assert.equal(
            services_requests_pg.flash_message,
            "VM Provision Request was Submitted, "
            "you will be notified when your VMs are ready")
        services_requests_pg.approve_request(1)
        services_requests_pg.wait_for_request_status(
            "Last 24 Hours",
            "Finished", 12)

    def assert_vm_state(
            self,
            provisioning_data,
            current_page,
            current_state,
            random_name):
        ''' Asserts that the VM is created in the expected state '''
        if "instance_type" in provisioning_data:
            vm_pg = current_page.header.site_navigation_menu(
                'Clouds').sub_navigation_menu(
                'Instances').click()
            vm_pg.refresh()
            vm_pg.wait_for_state_change('%s%s' % (
                provisioning_data["vm_name"],
                random_name),
                current_state,
                12)
        else:
            vm_pg = current_page.header.site_navigation_menu(
                'Infrastructure').sub_navigation_menu(
                'Virtual Machines').click()
            vm_pg.refresh()
            vm_pg.wait_for_vm_state_change('%s%s' % (
                provisioning_data["vm_name"],
                random_name), current_state, 12)
        Assert.equal(vm_pg.quadicon_region.get_quadicon_by_title(
            '%s%s' % (provisioning_data["vm_name"], random_name))
            .current_state, current_state,
            "vm not in correct state: " + current_state)
        return vm_pg

    def teardown_remove_first_vm(
            self,
            mgmt_sys_api_clients,
            vmware_linux_setup_data):
        '''Removes first VM created for cloning/retirement'''
        provider = mgmt_sys_api_clients.values()[0]
        if (vmware_linux_setup_data["vm_name"] + "/" +
                vmware_linux_setup_data["vm_name"] + ".vmx") \
                in provider.list_vm() or \
                vmware_linux_setup_data["vm_name"] \
                in provider.list_vm():
            provider.delete_vm(vmware_linux_setup_data["vm_name"])

    def teardown_remove_from_provider(
            self,
            db_session,
            soap_client,
            provider,
            vm_name):
        '''Stops a VM and removes VM or Template from provider'''
        for name, guid, power_state, template in db_session.query(
                db.Vm.name, db.Vm.guid, db.Vm.power_state, db.Vm.template):
            if vm_name in name:
                if power_state == 'on':
                    result = soap_client.service.EVMSmartStop(guid)
                    Assert.equal(result.result, 'true')
                    break
                else:
                    print "Template found or VM is off"
                    if template:
                        print "Template to be deleted from provider"
                        soap_client.service.EVMDeleteVmByName(vm_name)
                    break
        else:
            raise Exception("Couldn't find VM or Template")
        if (vm_name + "/" + vm_name + ".vmx") in provider.list_vm() or \
                vm_name in provider.list_vm():
            provider.delete_vm(vm_name)
            soap_client.service.EVMDeleteVmByName(vm_name)
