# from cfme.modeling.base import parent_of_type
# from cfme.utils.appliance import ViaREST, MiqImplementationContext
# from . import RegionCollection, ZoneCollection, ServerCollection, Server, Zone, Region
# @MiqImplementationContext.external_for(RegionCollection.all, ViaREST)
# def region_all(self):
#     self.appliance.rest_api.collections.regions.reload()
#     region_collection = self.appliance.rest_api.collections.regions
#     regions = [self.instantiate(region.region) for region in region_collection]
#     return regions
# @MiqImplementationContext.external_for(ZoneCollection.all, ViaREST)
# def zone_all(self):
#     zone_collection = self.appliance.rest_api.collections.zones
#     zones = []
#     parent = self.filters.get('parent')
#     for zone in zone_collection:
#         zone.reload(attributes=['region_number'])
#         if parent and zone.region_number != parent.number:
#             continue
#         zones.append(self.instantiate(
#             name=zone.name, description=zone.description, id=zone.id
#         ))
#     # TODO: This code needs a refactor once the attributes can be loaded from the collection
#     return zones
# @MiqImplementationContext.external_for(ServerCollection.all, ViaREST)
# def server_all(self):
#     server_collection = self.appliance.rest_api.collections.servers
#     servers = []
#     parent = self.filters.get('parent')
#     slave_only = self.filters.get('slave', False)
#     for server in server_collection:
#         server.reload(attributes=['zone_id'])
#         if parent and server.zone_id != parent.id:
#             continue
#         if slave_only and server.is_master:
#             continue
#         servers.append(self.instantiate(name=server.name, sid=server.id))
#     # TODO: This code needs a refactor once the attributes can be loaded from the collection
#     return servers
# @MiqImplementationContext.external_for(ServerCollection.get_master, ViaREST)
# def get_master(self):
#     server_collection = self.appliance.rest_api.collections.servers
#     server = server_collection.find_by(is_master=True)[0]
#     return self.instantiate(name=server.name, sid=server.id)
# @MiqImplementationContext.external_for(Server.zone, ViaREST)
# def zone(self):
#     possible_parent = parent_of_type(self, Zone)
#     if self._zone:
#         return self._zone
#     elif possible_parent:
#         self._zone = possible_parent
#     else:
#         server_res = self.appliance.rest_api.collections.servers.find_by(id=self.sid)
#         server = server_res[0]
#         server.reload(attributes=['zone'])
#         zone = server.zone
#         zone_obj = self.appliance.collections.zones.instantiate(
#             name=zone.name, description=zone.description, id=zone.id
#         )
#         self._zone = zone_obj
#     return self._zone
# @MiqImplementationContext.external_for(Server.slave_servers, ViaREST)
# def slave_servers(self):
#     return self.zone.collections.servers.filter({'slave': True}).all()
# @MiqImplementationContext.external_for(Zone.region, ViaREST)
# def region(self):
#     possible_parent = parent_of_type(self, Region)
#     if self._region:
#         return self._region
#     elif possible_parent:
#         self._region = possible_parent
#     else:
#         zone_res = self.appliance.rest_api.collections.zones.find_by(id=self.id)
#         zone = zone_res[0]
#         zone.reload(attributes=['region_number'])
#         region_obj = self.appliance.collections.regions.instantiate(number=zone.region_number)
#         self._region = region_obj
#     return self._region
