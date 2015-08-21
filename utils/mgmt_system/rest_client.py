import requests
import os
from exceptions import RestClientException

requests.packages.urllib3.disable_warnings()


class BearerTokenAuth(requests.auth.AuthBase):
    """Attaches a bearer token to the given request object"""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer {}'.format(self.token)
        return r


class ContainerClient(object):

    def __init__(self, hostname, auth, protocol="https", port=6443, entry='api/v1', verify=False):
        """Simple REST API client for container management systems

        Args:
            hostname: String with the hostname or IP address of the server (e.g. '10.11.12.13')
            auth: Either a (user, pass) sequence or a string with token
            protocol: Protocol to use for communication with the server
            port: Port to use
            entry: Entry point of the REST API
            verify: 'True' if we want to verify SSL, 'False' otherwise
        """
        self.api_entry = "{}://{}:{}/{}".format(protocol, hostname, port, entry)
        self.verify = verify
        if type(auth) in (list, set, tuple):
            self.auth = auth
        elif type(auth) is str:
            self.auth = BearerTokenAuth(auth)
        else:
            raise RestClientException('Invalid auth object')

    def get(self, entity_type, name=None, namespace=None):
        """Sends a request to fetch an entity of specific type

        Fetches a single entity if its name is provided or all of given type if name is ommited.

        Note:
            Some entities are tied to namespaces (projects).
            To fetch these by name, namespace has to be provided as well.

        Return:
            Tuple containing status code and json response with requested entity/entities.
        """
        path = '{}s'.format(entity_type)
        if name is not None:
            if namespace is not None:
                path = os.path.join('namespaces/{}'.format(namespace), path)
            path = os.path.join(path, '{}'.format(name))
        r = self.raw_get(path)
        return (r.status_code, r.json() if r.ok else None)

    def raw_get(self, path):
        return requests.get(
            os.path.join(self.api_entry, path), auth=self.auth, verify=self.verify)
