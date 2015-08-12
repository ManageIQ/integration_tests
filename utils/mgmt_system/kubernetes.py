from collections import namedtuple
from base import ContainerMgmtSystemAPIBase
from rest_client import ContainerClient

"""
Related yaml structures:

[cfme_data]
management_systems:
    kubernetes:
        name: My kubernetes
        type: kubernetes
        hostname: 10.12.13.14
        port: 6443
        credentials: kubernetes
        authenticate: true
        rest_protocol: https

[credentials]
kubernetes:
    username: admin
    password: secret
    token: mytoken
"""

# Below are simplified representations of CFME k8s objects that should cover most of our needs
Container = namedtuple('Container', ['name', 'cg_name', 'image'])
Image = namedtuple('Image', ['name', 'tag', 'id'])
# Images are equal if their ids match
Image.__eq__ = lambda self, other: self.id == other.id
ImageRegistry = namedtuple('ImageRegistry', ['host', 'port'])
Project = namedtuple('Project', ['name'])
Node = namedtuple('Node', ['name', 'ready', 'cpu', 'memory'])
ContainerGroup = namedtuple(
    'ContainerGroup', ['name', 'project_name', 'restart_policy', 'dns_policy'])
ReplicationController = namedtuple(
    'ReplicationController', ['name', 'project_name', 'replicas', 'current_replicas'])
Service = namedtuple('Service', ['name', 'project_name', 'portal_ip', 'session_affinity'])


class Kubernetes(ContainerMgmtSystemAPIBase):
    def __init__(self, hostname, protocol="https", port=6443, entry='api/v1', **kwargs):
        self.hostname = hostname
        self.username = kwargs.get('username', '')
        self.password = kwargs.get('password', '')
        self.token = kwargs.get('token', '')
        self.auth = self.token if self.token else (self.username, self.password)
        self.api = ContainerClient(hostname, self.auth, protocol, port, entry)

    def _parse_image_info(self, image_str):
        """Splits full image name into registry, name and tag

        Both registry and tag are optional, name is always present.

        Example:
            localhost:5000/nginx:latest => localhost:5000, nginx, latest
        """
        registry, image_str = image_str.split('/', 1) if '/' in image_str else ('', image_str)
        name, tag = image_str.split(':') if ':' in image_str else (image_str, '')
        return registry, name, tag

    def info(self):
        """Returns information about the cluster - number of CPUs and memory in GB"""
        aggregate_cpu, aggregate_mem = 0, 0
        for node in self.list_node():
            aggregate_cpu += node.cpu
            aggregate_mem += node.memory
        return {'cpu': aggregate_cpu, 'memory': aggregate_mem}

    def list_container(self):
        """Returns list of containers (derived from pods)"""
        entities = []
        entities_j = self.api.get('pod')[1]['items']
        for entity_j in entities_j:
            conts_j = entity_j['spec']['containers']
            for cont_j in conts_j:
                cont = Container(cont_j['name'], entity_j['metadata']['name'], cont_j['image'])
                if cont not in entities:
                    entities.append(cont)
        return entities

    def list_container_group(self):
        """Returns list of container groups (pods)"""
        entities = []
        entities_j = self.api.get('pod')[1]['items']
        for entity_j in entities_j:
            meta, spec = entity_j['metadata'], entity_j['spec']
            entity = ContainerGroup(
                meta['name'], meta['namespace'], spec['restartPolicy'], spec['dnsPolicy'])
            entities.append(entity)
        return entities

    def list_service(self):
        """Returns list of services"""
        entities = []
        entities_j = self.api.get('service')[1]['items']
        for entity_j in entities_j:
            meta, spec = entity_j['metadata'], entity_j['spec']
            entity = Service(
                meta['name'], meta['namespace'], spec['clusterIP'], spec['sessionAffinity'])
            entities.append(entity)
        return entities

    def list_replication_controller(self):
        """Returns list of replication controllers"""
        entities = []
        entities_j = self.api.get('replicationcontroller')[1]['items']
        for entity_j in entities_j:
            meta, spec, status = entity_j['metadata'], entity_j['spec'], entity_j['status']
            entity = ReplicationController(
                meta['name'], meta['namespace'], spec['replicas'], status['replicas'])
            entities.append(entity)
        return entities

    def list_image(self):
        """Returns list of images (derived from pods)"""
        entities = []
        entities_j = self.api.get('pod')[1]['items']
        for entity_j in entities_j:
            imgs_j = entity_j['status']['containerStatuses']
            for img_j in imgs_j:
                _, name, tag = self._parse_image_info(img_j['image'])
                img = Image(name, tag, img_j['imageID'])
                if img not in entities:
                    entities.append(img)
        return entities

    def list_node(self):
        """Returns list of nodes"""
        entities = []
        entities_j = self.api.get('node')[1]['items']
        for entity_j in entities_j:
            meta, status = entity_j['metadata'], entity_j['status']
            cond, cap = status['conditions'][0], status['capacity']
            cpu = int(cap['cpu'])
            memory = int(round(int(cap['memory'][:-2]) * 0.00000102400))  # KiB to GB
            entity = Node(meta['name'], cond['status'], cpu, memory)
            entities.append(entity)
        return entities

    def list_image_registry(self):
        """Returns list of image registries (derived from pods)"""
        entities = []
        entities_j = self.api.get('pod')[1]['items']
        for entity_j in entities_j:
            imgs_j = entity_j['status']['containerStatuses']
            for img_j in imgs_j:
                registry, _, __ = self._parse_image_info(img_j['image'])
                if not registry:
                    continue
                host, port = registry.split(':') if ':' in registry else (registry, '')
                entity = ImageRegistry(host, port)
                if entity not in entities:
                    entities.append(entity)
        return entities

    def list_project(self):
        """Returns list of projects (namespaces in k8s)"""
        entities = []
        entities_j = self.api.get('namespace')[1]['items']
        for entity_j in entities_j:
            meta = entity_j['metadata']
            entity = Project(meta['name'])
            entities.append(entity)
