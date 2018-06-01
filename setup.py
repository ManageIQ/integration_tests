# dummy for editable installs
import sys

import os
from setuptools import setup, find_packages

# just cleanly exit on readthedocs
if os.environ.get('READTHEDOCS') == 'True':
    sys.exit()
elif 'develop' in sys.argv or 'egg_info' in sys.argv:
    pass
else:
    sys.exit('this is a hack, use pip install -e')

setup(
    name='manageiq-integration-tests',

    entry_points={
        'console_scripts': [
            'miq = cfme.scripting.miq:cli',
            'miq-release = cfme.utils.release:main',
            'miq-artifactor-server = artifactor.__main__:main',
            'miq-runtest = cfme.scripting.runtest:main',
            'miq-ipython = cfme.scripting.ipyshell:main',
            'miq-selenium-container = cfme.utils.dockerbot.sel_container:main'
        ],
        'manageiq.provider_categories':
        [
            'infra = cfme.infrastructure.provider:InfraProvider',
            'cloud = cfme.cloud.provider:CloudProvider',
            'containers = cfme.containers.provider:ContainersProvider',
            'physical = cfme.physical.provider:PhysicalProvider',
            'networks = cfme.networks.provider:NetworkProvider',
        ],
        'manageiq.provider_types.infra': [
            'virtualcenter = cfme.infrastructure.provider.virtualcenter:VMwareProvider',
            'scvmm = cfme.infrastructure.provider.scvmm:SCVMMProvider',
            'rhevm = cfme.infrastructure.provider.rhevm:RHEVMProvider',
            'openstack_infra = cfme.infrastructure.provider.openstack_infra:OpenstackInfraProvider',
            'kubevirt = cfme.infrastructure.provider.kubevirt:KubeVirtProvider'
        ],
        'manageiq.provider_types.cloud': [
            'ec2 = cfme.cloud.provider.ec2:EC2Provider',
            'openstack = cfme.cloud.provider.openstack:OpenStackProvider',
            'azure = cfme.cloud.provider.azure:AzureProvider',
            'gce = cfme.cloud.provider.gce:GCEProvider',
            'vcloud = cfme.cloud.provider.vcloud:VmwareCloudProvider',
        ],
        'manageiq.provider_types.containers': [
            'openshift = cfme.containers.provider.openshift:OpenshiftProvider',
        ],
        'manageiq.provider_types.physical': [
            'lenovo = cfme.physical.provider.lenovo:LenovoProvider'
        ],
        'manageiq.provider_types.networks': [
            'nuage = cfme.networks.provider.nuage:NuageProvider'
        ],
        'manageiq.vm_categories':
        [
            'infra = cfme.infrastructure.virtual_machines:InfraVm',
            'cloud = cfme.cloud.instance:Instance'
        ],
        'manageiq.vm_types.cloud':
        [
            'ec2 = cfme.cloud.instance.ec2:EC2Instance',
            'gce = cfme.cloud.instance.gce:GCEInstance',
            'openstack = cfme.cloud.instance.openstack:OpenStackInstance',
            'azure = cfme.cloud.instance.azure:AzureInstance'
        ],
        'manageiq.template_categories':
        [
            'infra = cfme.infrastructure.virtual_machines:Template',
            'cloud = cfme.cloud.instance.image:Image'
        ],
        'manageiq.auth_provider_types':
        [
            'amazon = cfme.utils.auth:AmazonAuthProvider',
            'freeipa = cfme.utils.auth:FreeIPAAuthProvider',
            'openldap = cfme.utils.auth:OpenLDAPAuthProvider',
            'openldaps = cfme.utils.auth:OpenLDAPSAuthProvider',
            'ad = cfme.utils.auth:ActiveDirectoryAuthProvider'
        ],
        'manageiq.appliance_collections':
        [
            'actions = cfme.control.explorer.actions:ActionCollection',
            'alert_profiles = cfme.control.explorer.alert_profiles:AlertProfileCollection',
            'alerts = cfme.control.explorer.alerts:AlertCollection',
            'ansible_credentials = cfme.ansible.credentials:CredentialsCollection',
            'ansible_playbooks = cfme.ansible.playbooks:PlaybooksCollection',
            'ansible_repositories = cfme.ansible.repositories:RepositoryCollection',
            'balancers = cfme.networks.balancer:BalancerCollection',
            'block_managers = cfme.storage.manager:BlockManagerCollection',
            'button_groups = cfme.automate.buttons:ButtonGroupCollection',
            'buttons = cfme.automate.buttons:ButtonCollection',
            'candus = cfme.configure.configuration.region_settings:CANDUCollection',
            ('catalog_bundles = '
                'cfme.services.catalogs.catalog_items.catalog_bundles:CatalogBundlesCollection'),
            'catalog_items = cfme.services.catalogs.catalog_items:CatalogItemsCollection',
            'catalogs = cfme.services.catalogs.catalog:CatalogCollection',
            'cloud_av_zones = cfme.cloud.availability_zone:AvailabilityZoneCollection',
            'cloud_flavors = cfme.cloud.flavor:FlavorCollection',
            'cloud_images = cfme.cloud.instance.image:ImageCollection',
            'cloud_instances = cfme.cloud.instance:InstanceCollection',
            'cloud_keypairs = cfme.cloud.keypairs:KeyPairCollection',
            'cloud_networks = cfme.networks.cloud_network:CloudNetworkCollection',
            'cloud_providers = cfme.cloud.provider:CloudProviderCollection',
            'cloud_stacks = cfme.cloud.stack:StackCollection',
            'cloud_tenants = cfme.cloud.tenant:TenantCollection',
            'clusters = cfme.infrastructure.cluster:ClusterCollection',
            'conditions = cfme.control.explorer.conditions:ConditionCollection',
            'container_image_registries = cfme.containers.image_registry:ImageRegistryCollection',
            'container_images = cfme.containers.image:ImageCollection',
            'container_nodes = cfme.containers.node:NodeCollection',
            'container_pods = cfme.containers.pod:PodCollection',
            'container_projects = cfme.containers.project:ProjectCollection',
            'containers_providers = cfme.containers.provider:ContainersProviderCollection',
            'container_replicators = cfme.containers.replicator:ReplicatorCollection',
            'container_routes = cfme.containers.route:RouteCollection',
            'container_services = cfme.containers.service:ServiceCollection',
            'container_templates = cfme.containers.template:TemplateCollection',
            'container_volumes = cfme.containers.volume:VolumeCollection',
            'containers = cfme.containers.container:ContainerCollection',
            'customization_templates = cfme.infrastructure.pxe:CustomizationTemplateCollection',
            ('dashboard_report_widgets = '
                'cfme.intelligence.reports.widgets:DashboardReportWidgetsCollection'),
            'dashboards = cfme.dashboard:DashboardCollection',
            'datastores = cfme.infrastructure.datastore:DatastoreCollection',
            'deployment_roles = cfme.infrastructure.deployment_roles:DeploymentRoleCollection',
            ('diagnostic_workers = '
                'cfme.configure.configuration.diagnostics_settings:DiagnosticWorkersCollection'),
            'domains = cfme.automate.explorer.domain:DomainCollection',
            ('generic_object_definitions = '
                'cfme.generic_objects.definition:GenericObjectDefinitionCollection'),
            'generic_objects = cfme.generic_objects.instance:GenericObjectInstanceCollection',
            'groups = cfme.configure.access_control:GroupCollection',
            'hosts = cfme.infrastructure.host:HostCollection',
            'infra_providers = cfme.infrastructure.provider:InfraProviderCollection',
            'infra_templates = cfme.infrastructure.virtual_machines:InfraTemplateCollection',
            'infra_vms = cfme.infrastructure.virtual_machines:InfraVmCollection',
            'infrastructure_mapping = cfme.v2v.migrations:InfrastructureMappingCollection',
            'map_tags = cfme.configure.configuration.region_settings:MapTagsCollection',
            'network_floating_ips = cfme.networks.floating_ips:FloatingIpCollection',
            'network_ports = cfme.networks.network_port:NetworkPortCollection',
            'network_providers = cfme.networks.provider:NetworkProviderCollection',
            'network_routers = cfme.networks.network_router:NetworkRouterCollection',
            'network_security_groups = cfme.networks.security_group:SecurityGroupCollection',
            'network_subnets = cfme.networks.subnet:SubnetCollection',
            'network_topology_elements = cfme.networks.topology:NetworkTopologyElementsCollection',
            'object_managers = cfme.storage.manager:ObjectManagerCollection',
            ('object_store_containers = '
                'cfme.storage.object_store_container:ObjectStoreContainerCollection'),
            'object_store_objects = cfme.storage.object_store_object:ObjectStoreObjectCollection',
            'openstack_nodes = cfme.infrastructure.openstack_node:OpenstackNodeCollection',
            ('orchestration_templates = '
                'cfme.services.catalogs.orchestration_template:OrchestrationTemplatesCollection'),
            'physical_providers = cfme.physical.provider:PhysicalProviderCollection',
            'physical_servers = cfme.physical.physical_server:PhysicalServerCollection',
            'policies = cfme.control.explorer.policies:PolicyCollection',
            'policy_profiles = cfme.control.explorer.policy_profiles:PolicyProfileCollection',
            'projects = cfme.configure.access_control:ProjectCollection',
            ('provisioning_dialogs = '
                'cfme.automate.provisioning_dialogs:ProvisioningDialogsCollection'),
            'regions = cfme.base:RegionCollection',
            'reports = cfme.intelligence.reports.reports:ReportsCollection',
            'report_dashboards = cfme.intelligence.reports.dashboards:DashboardsCollection',
            'requests = cfme.services.requests:RequestCollection',
            'resource_pools = cfme.infrastructure.resource_pool:ResourcePoolCollection',
            'roles = cfme.configure.access_control:RoleCollection',
            'saved_reports = cfme.intelligence.reports.saved:SavedReportsCollection',
            'schedules = cfme.intelligence.reports.schedules:ScheduleCollection',
            'security_groups = cfme.cloud.security_groups:SecurityGroupCollection',
            'servers = cfme.base:ServerCollection',
            'service_dialogs = cfme.automate.dialog_collection_pick:collection_pick',
            'system_image_types = cfme.infrastructure.pxe:SystemImageTypeCollection',
            ('system_schedules = '
                'cfme.configure.configuration.system_schedules:SystemSchedulesCollection'),
            'tasks = cfme.configure.tasks:TasksCollection',
            'tenants = cfme.configure.access_control:TenantCollection',
            'time_profiles = cfme.configure.settings:TimeProfileCollection',
            'users = cfme.configure.access_control:UserCollection',
            'v2v_mappings = cfme.v2v.migrations:InfrastructureMappingCollection',
            'v2v_plans = cfme.v2v.migrations:MigrationPlanCollection',
            'volume_backups = cfme.storage.volume_backup:VolumeBackupCollection',
            'volume_snapshots = cfme.storage.volume_snapshot:VolumeSnapshotCollection',
            'volumes = cfme.storage.volume:VolumeCollection',
            'zones = cfme.base:ZoneCollection'
        ],
        'pytest11':
        [
            'cfme = cfme.test_framework.pytest_plugin',
        ]
    },
    packages=find_packages(),
)
