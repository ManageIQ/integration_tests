from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.rest import ViaREST

from . import UserCollection, GroupCollection


@MiqImplementationContext.external_for(UserCollection.create, ViaREST)
def u_create(self, name=None, credential=None, email=None, group=None, cancel=False):

    user = self.instantiate(
        name=name, credential=credential, email=email, group=group)

    data_dict = {
        'name': user.name,
        'userid': user.credential.principal,
        'password': user.credential.secret,
        'email': user.email,
        'group': {
            'description': user.group.description
        }
    }

    self.appliance.rest_api.collections.users.action.create(data_dict)
    return user


@MiqImplementationContext.external_for(GroupCollection.create, ViaREST)
def g_create(self, description=None, role=None, tenant=None, ldap_credentials=None,
           user_to_lookup=None, tag=None, host_cluster=None, vm_template=None, cancel=False):

    if ldap_credentials or user_to_lookup or tag or host_cluster or vm_template:
        raise Exception('The following attributes are not yet supported via REST create '
                        '[ldap_credentials, user_to_lookup, tag, host_cluster, vm_template]')

    group = self.instantiate(
        description=description, role=role, tenant=tenant, ldap_credentials=ldap_credentials,
        user_to_lookup=user_to_lookup, tag=tag, host_cluster=host_cluster,
        vm_template=vm_template)

    tenant = 1 if not group.tenant else group.tenant.id

    data_dict = {
        'description': group.description,
        'tenant': {'id': tenant},
        'role': {'name': role.name},
    }

    self.appliance.rest_api.collections.groups.action.create(data_dict)
    return group
