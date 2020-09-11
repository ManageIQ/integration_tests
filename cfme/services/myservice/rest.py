from cfme.services.myservice import MyService
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.rest import ViaREST


@MiqImplementationContext.external_for(MyService.add_resource_generic_object, ViaREST)
def add_resource_generic_object(self, gen_obj):
    """ Add a generic object instance to the service """
    self.rest_api_entity.action.add_resource(
        resource=self.appliance.rest_api.collections.generic_objects.get(
            name=gen_obj.name
        )._ref_repr()
    )


@MiqImplementationContext.external_for(MyService.retire, ViaREST)
def retire(self, wait=True):
    retire_request = self.rest_api_entity.action.request_retire()
    service_request = self.appliance.collections.requests.instantiate(
        description=retire_request.description
    )
    if wait:
        service_request.wait_for_request()
    return service_request
