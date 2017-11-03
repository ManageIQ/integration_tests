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
            'service_dialogs = cfme.automate.service_dialogs:DialogCollection',
            'domains = cfme.automate.explorer.domain:DomainCollection',
            'keypairs = cfme.cloud.keypairs:KeyPairCollection',
            'stacks = cfme.cloud.stack:StackCollection',
            'cloud_tenants = cfme.cloud.tenant:TenantCollection',
            'tenants = cfme.configure.access_control:TenantCollection',
            'projects = cfme.configure.access_control:ProjectCollection',
            'candus = cfme.configure.configuration.region_settings:CANDUCollection',
            'nodes = cfme.containers.node:NodeCollection',
            'dashboards = cfme.dashboard:DashboardCollection',
            'clusters = cfme.infrastructure.cluster:ClusterCollection',
            'hosts = cfme.infrastructure.host:HostCollection',
            'deployment_roles = cfme.infrastructure.deployment_roles:DeploymentRoleCollection',
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
            'volumes = cfme.storage.volume:VolumeCollection',
            'block_managers = cfme.storage.manager:BlockManagerCollection',
            'object_managers = cfme.storage.manager:ObjectManagerCollection',
            'object_store_objects = cfme.storage.object_store_object:ObjectStoreObjectCollection',
            ('object_store_containers = '
                'cfme.storage.object_store_container:ObjectStoreContainerCollection'),
            'zones = cfme.base:ZoneCollection'
        ],
        'pytest11':
        [
            'cfme = cfme.test_framework.pytest_plugin',
        ]
    },
    packages=find_packages(),
)
