Adding a New Provider Type
==========================

Introduction
------------

Though not an exhaustive guide, this page details some of the tasks that need to be carried out in
order for a new provider to be added and suported in the ManageIQ integration_tests framework.

wrapanapi
---------

wrapanapi is a key component in the testing process. Each provider that we test has its own class
within wrapanapi. The name of the project gives some indication as to what it does, it simply
wraps-an-API. People ask why we use a wrapper around existing python library APIs. The answer is
because we try to maintain a common API across the providers APIs where possible.

Validating information on the provider is important. When testing ManageIQ we don't just rely on
the information it gives us, we need to ensure that the information is correct. To do that, we call
out to the provider itself and validate that if ManageIQ says there are 25 VMs, that there really
are 25VMs. Some simple methods are often present on the wrapanapi management class with names like
``num_vm``. These simply return a count of the number of VMs that are present in the normal context.

You may often find that there are options to the method too. wrapanapi is designed to work primarily
with ManageIQ for testing, but is also an Open Source system, allowing anyone to use it as a simple
management tool for multiple provider types.

The first step in the process of adding a new provider is making a rudimentary wrapanapi class. This
should always be called ``ProviderSystem``, where Provider is a short name denoting your new provider.

Provider Type
--------------

If your provider doesn't conform to the currently existing types, which broadly consist of Infrastructure
and Cloud virtualization, Containers and Middleware, you will need a new provider type. You can think
of this as a kind of super class that will be a reference point for all future classes of the same
type. Though it is not entirely necessary. It is nice to create these to give others a springboard
if they are creating a provider which is of the same type as yours.

The next part of the process is to create the provider type class within the integration_tests repository.
This class will be used to represent your providers type in the ManageIQ system. It is your singular point
of reference and will become your go to point of contact for all provider type related operations.

An example of a new provider type is below, we will take a moment to walk through the various parts of it.

.. code-block::python

    from widgetastic.utils import Fillable

    from navmazing import NavigateToObject, NavigateToSibling

    from cfme.base.ui import BaseLoggedInPage
    from cfme.utils.pretty import Pretty
    from cfme.common.provider import BaseProvider
    from cfme.common.provider_views import PhysicalProvidersView
    from cfme.utils.appliance import Navigatable
    from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep

    from cfme.base.ui import Server


    class PhysicalProvider(Pretty, BaseProvider, Fillable):
        """
        Abstract model of an infrastructure provider in cfme. See VMwareProvider or RHEVMProvider.
        """
        provider_types = {}
        category = "physical"
        pretty_attrs = ['name']
        STATS_TO_MATCH = ['num_server']
        string_name = "Physical Infrastructure"

        def __init__(
                self, appliance=None, name=None, key=None, endpoints=None):
            Navigatable.__init__(self, appliance=appliance)
            self.endpoints = prepare_endpoints(endpoints)
            self.name = name
            self.key = key

    @navigator.register(Server, 'PhysicalProviders')
    @navigator.register(PhysicalProvider, 'All')
    class All(CFMENavigateStep):
        # This view will need to be created
        VIEW = PhysicalProvidersView
        prerequisite = NavigateToObject(Server, 'LoggedIn')

        def step(self):
            self.prerequisite_view.navigation.select('Compute', 'Physical Infrastructure', 'Providers')

        def resetter(self):
            # Reset view and selection
            pass

The example above does a few things and we shall ignore the imports. Firstly we define the
PhysicalProvider class. Note that this follows the same format as in wrapanapi. Also note that this
class can't really **do** anything. It is a placeholder that knows about things like, how to list
all the providers which are of type ``physical``.

The ``category`` attribute is very important. It is used to classify your provider classes.
``STATS_TO_MATCH`` is a helper which is invoked during provider validation and will run the same
method on both the ManageIQ side, and the wrapanapi side, to ensure parity.
``endpoints``, ``name``, ``key`` are really the base level components to any provider. The endpoint
describes how to contact the provider, what its credentials are and its various methods of communication.
ManageIQ can sometimes interact with multiple endpoints on a provider. This allows that communication
to be represented inside the testing framework and to fill in the multiple endpoint forms in the UI.

The main credential is always called ``default`` and endpoints takes the form of a dictionary which
is used to instantiate some ``Endpoint`` objects. Please refer to existing providers for more
information on this.

Lastly there is a Navigation step defined. This is using the ``navmazing`` component and should
be used as an example only. You should go and look up further examples of the ``navmazing`` and
``widgetastic`` systems to understand how to interact with the UI. In this example, we are creating
reference to an ``All`` destination which will, in the UI, navigate to a page showing **all** the
physical infrastructure providers.

Provider Class
--------------

Now that we have a provider type, or perhaps we already have one, we need to create a provider class.
This class is a specific implementation of the provider. Anything which is not common across either
the providers as a whole, or the even within the category of the provider, is recorded here.

.. code-block:: python

    from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm

    from . import PhysicalProvider


    class BigBadEndpoint(DefaultEndpoint):
        pass


    class BigBadEndpointForm(DefaultEndpointForm):
        pass


    class BigBadProvider(PhysicalProvider):
        type_name = 'bigbad'
        endpoints_form = BigBadEndpointForm
        string_name = "Ems Physical Infras"
        mgmt_class = BigBadSystem                                     # The reference to wrapanapi

        def __init__(self, appliance, name=None, key=None, endpoints=None):
            super(BigBadProvider, self).__init__(
                appliance=appliance, name=name, key=key, endpoints=endpoints
            )

        @classmethod
        def from_config(cls, prov_config, prov_key, appliance=None):
            endpoint = BigBadEndpoint(**prov_config['endpoints']['default'])
            return cls(name=prov_config['name'],
                       endpoints={endpoint.name: endpoint},
                       key=prov_key,
                       appliance=appliance)

        @property
        def view_value_mapping(self):
            return {'name': self.name,
                    'prov_type': 'BigBad Provider'
                    }

To note are the endpoints. You can see here that we are inheriting some default forms. These are
used for almost every provider. They provide support for simple username/password combinations.
In the ``from_config`` method, we have provider specific instantiation of the class. You can
see that we instantiate the ``BigBadEndpoint`` class by passing it information from the
``prov_config``. This is the data which is stored in the yamls and looks similar to the following.

.. code-block:: yaml

        big-bad-prov:
            name: bigbad
            type: bigbad
            tags:
                - default
            endpoints:
                default:
                    ipaddress: xx.xx.xx.xx
                    hostname: bigbadprovider.something.com
                    credentials: mycreds

The last point of note in this example is the ``view_value_mapping`` property. This is responsible
for returning specific form data what is not covered by endpoints. In ManageIQ, there is a need to
select the provider type when adding a new provider and this providers that type.

Registering your Provider
-------------------------

Before your provider can be used in any tests it first must be registered. This is achieved by adding
it to setup.py. You should be familiar with the entrypoints system to do this. Below you can
see the examples of how the provider is added for the previous types.

.. code-block:: python

    entry_points={
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
            'openshift = cfme.containers.provider.openshift:OpenshiftProvider',
        ],
        'manageiq.provider_types.physical': [
            'hawkular = cfme.middleware.provider.bigbad:BigBadProvider',
        ],
    }
