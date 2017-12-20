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
            'miq-release = scripts.release:main',
            'miq-artifactor-server = artifactor.__main__:main',
            'miq-runtest = cfme.scripting.runtest:main',
            'miq-ipython = cfme.scripting.ipyshell:main',
            'miq-selenium-container = scripts.dockerbot.sel_container:main'
        ],
        'manageiq.provider_categories':
        [
            'infra = cfme.infrastructure.provider:InfraProvider',
            'cloud = cfme.cloud.provider:CloudProvider',
            'middleware = cfme.middleware.provider:MiddlewareProvider',
            'containers = cfme.containers.provider:ContainersProvider',
            'physical = cfme.physical.provider:PhysicalProvider',
            'networks = cfme.networks.provider:NetworkProvider',
        ],
        'manageiq.provider_types.infra': [
            'virtualcenter = cfme.infrastructure.provider.virtualcenter:VMwareProvider',
            'scvmm = cfme.infrastructure.provider.scvmm:SCVMMProvider',
            'rhevm = cfme.infrastructure.provider.rhevm:RHEVMProvider',
            'openstack_infra = cfme.infrastructure.provider.openstack_infra:OpenstackInfraProvider',
        ],
        'manageiq.provider_types.cloud': [
            'ec2 = cfme.cloud.provider.ec2:EC2Provider',
            'openstack = cfme.cloud.provider.openstack:OpenStackProvider',
            'azure = cfme.cloud.provider.azure:AzureProvider',
            'gce = cfme.cloud.provider.gce:GCEProvider',
        ],
        'manageiq.provider_types.middleware': [
            'hawkular = cfme.middleware.provider.hawkular:HawkularProvider',
        ],
        'manageiq.provider_types.containers': [
            'kubernetes = cfme.containers.provider.kubernetes:KubernetesProvider',
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
            'infra = cfme.infrastructure.virtual_machines:Vm',
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
        'manageiq.appliance_collections':
        [
            'actions = cfme.control.explorer.actions:ActionCollection',
            'alerts = cfme.control.explorer.alerts:AlertCollection',
            'alert_profiles = cfme.control.explorer.alert_profiles:AlertProfileCollection',
            'conditions = cfme.control.explorer.conditions:ConditionCollection',
            ('diagnostic_workers = '
                'cfme.configure.configuration.diagnostics_settings:DiagnosticWorkersCollection'),
            'policies = cfme.control.explorer.policies:PolicyCollection',
            'policy_profiles = cfme.control.explorer.policy_profiles:PolicyProfileCollection',
            'ansible_credentials = cfme.ansible.credentials:CredentialsCollection',
            'ansible_playbooks = cfme.ansible.playbooks:PlaybooksCollection',
            'ansible_repositories = cfme.ansible.repositories:RepositoryCollection',
            'datastores = cfme.infrastructure.datastore:DatastoreCollection',
            'service_dialogs = cfme.automate.dialog_collection_pick:collection_pick',
            'domains = cfme.automate.explorer.domain:DomainCollection',
            'keypairs = cfme.cloud.keypairs:KeyPairCollection',
            'stacks = cfme.cloud.stack:StackCollection',
            'security_groups = cfme.cloud.security_groups:SecurityGroupCollection',
            'cloud_tenants = cfme.cloud.tenant:TenantCollection',
            'tenants = cfme.configure.access_control:TenantCollection',
            'projects = cfme.configure.access_control:ProjectCollection',
            'roles = cfme.configure.access_control:RoleCollection',
            'users = cfme.configure.access_control:UserCollection',
            'candus = cfme.configure.configuration.region_settings:CANDUCollection',
            'groups = cfme.configure.access_control:GroupCollection',
            'container_nodes = cfme.containers.node:NodeCollection',
            'dashboards = cfme.dashboard:DashboardCollection',
            'clusters = cfme.infrastructure.cluster:ClusterCollection',
            'hosts = cfme.infrastructure.host:HostCollection',
            'deployment_roles = cfme.infrastructure.deployment_roles:DeploymentRoleCollection',
            'customization_templates = cfme.infrastructure.pxe:CustomizationTemplateCollection',
            'system_image_types = cfme.infrastructure.pxe:SystemImageTypeCollection',
            'schedules = cfme.intelligence.reports.schedules:ScheduleCollection',
            ('system_schedules = '
                'cfme.configure.configuration.system_schedules:SystemSchedulesCollection'),
            'balancers = cfme.networks.balancer:BalancerCollection',
            'cloud_networks = cfme.networks.cloud_network:CloudNetworkCollection',
            'network_ports = cfme.networks.network_port:NetworkPortCollection',
            'network_routers = cfme.networks.network_router:NetworkRouterCollection',
            'network_providers = cfme.networks.provider:NetworkProviderCollection',
            'network_security_groups = cfme.networks.security_group:SecurityGroupCollection',
            'network_subnets = cfme.networks.subnet:SubnetCollection',
            'requests = cfme.services.requests:RequestCollection',
            'resource_pools = cfme.infrastructure.resource_pool:ResourcePoolCollection',
            'volumes = cfme.storage.volume:VolumeCollection',
            'volume_backups = cfme.storage.volume_backup:VolumeBackupCollection',
            'block_managers = cfme.storage.manager:BlockManagerCollection',
            'object_managers = cfme.storage.manager:ObjectManagerCollection',
            'object_store_objects = cfme.storage.object_store_object:ObjectStoreObjectCollection',
            ('object_store_containers = '
                'cfme.storage.object_store_container:ObjectStoreContainerCollection'),
            'container_images = cfme.containers.image:ImageCollection',
            'zones = cfme.base:ZoneCollection',
            'servers = cfme.base:ServerCollection',
            'regions = cfme.base:RegionCollection',
            'container_pods = cfme.containers.pod:PodCollection',
            'containers = cfme.containers.container:ContainerCollection',
            'container_image_registries = cfme.containers.image_registry:ImageRegistryCollection',
            'container_projects = cfme.containers.project:ProjectCollection',
            'container_replicators = cfme.containers.replicator:ReplicatorCollection',
            'container_routes = cfme.containers.route:RouteCollection',
            'container_services = cfme.containers.service:ServiceCollection',
            'container_templates = cfme.containers.template:TemplateCollection',
            'container_volumes = cfme.containers.volume:VolumeCollection',
            ('generic_object_definitions = '
                'cfme.generic_objects.definition:GenericObjectDefinitionCollection'),
            ('generic_objects = '
                'cfme.generic_objects.instance:GenericObjectInstanceCollection')
        ],
        'pytest11':
        [
            'cfme = cfme.test_framework.pytest_plugin',
        ]
    },
    packages=find_packages(),
)
