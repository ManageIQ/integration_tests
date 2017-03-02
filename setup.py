# dummy for editable installs
import sys
import os
from setuptools import setup, find_packages

# just cleanly exit on readthedocs
if os.environ.get('READTHEDOCS', None) == 'True':
    sys.exit()
elif 'develop' in sys.argv or 'egg_info' in sys.argv:
    pass
else:
    sys.exit('this is a hack, use pip install -e')

setup(
    name='manageiq-integration-tests',

    entry_points={
        'console_scripts': [
            'cfme-release = scripts.release:main',
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
    },
    packages=find_packages(),
)
