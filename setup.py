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
            'datastore = cfme.infrastructure.datastore:DatastoreCollection'
        ],
        'pytest11':
        [
            'cfme = cfme.test_framework.pytest_plugin',
        ]
    },
    packages=find_packages(),
)
