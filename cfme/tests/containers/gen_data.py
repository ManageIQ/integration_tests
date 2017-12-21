import fauxfactory

from wrapanapi.containers.project import Project
# from wrapanapi.containers.providers import openshift
# from wrapanapi.containers.deployment_config import DeploymentConfig
from wrapanapi.containers.image_registry import ImageRegistry
from wrapanapi.containers.image import Image
from wrapanapi.containers.pod import Pod
from wrapanapi.containers.service import Service
from wrapanapi.containers.node import Node
from wrapanapi.containers.replicator import Replicator
from wrapanapi.containers.route import Route
from wrapanapi.containers.template import Template
from wrapanapi.containers.volume import Volume


def gen_mgmt_project(provider, **kwargs):
    """Generate a project resource on given provider using wrapanapi"""
    project_namespace = kwargs.get('project_namespace', fauxfactory.gen_alpha().lower())
    project = Project(provider.mgmt, project_namespace)
    payload_default = {"metadata": {"name": project.name}}
    payload = kwargs.get('payload', payload_default)
    return project.create(provider.mgmt, payload=payload)


# JUWATTS
def gen_mgmt_image(provider, **kwargs):
    """Generate a image resource on a given provider using wrapanapi"""
    image_name = kwargs.get('image_name', 'some.test.image')
    sha_sum = kwargs.get('sha256', fauxfactory.gen_alphanumeric(64))
    return Image(provider.mgmt, image_name,
                 'sha256:{}'.format(sha_sum))


def gen_mgmt_pod(provider, **kwargs):
    """Generate a Pod resource on a given provider using wrapanapi"""
    pod_name = kwargs.get('pod_name', 'some-test-pod')
    pod_namespace = kwargs.get('pod_namespace', 'default')
    pod = Pod(provider.mgmt, pod_name, pod_namespace)
    payload_default = {
        "kind": "Pod",
        "apiVersion": "v1",
        "metadata": {
            "name": pod.name,
            "namespace": pod.namespace,
            "labels": {
                "name": pod.name
            }
        },
        "spec": {
            "containers": [
                {
                    "name": pod.name,
                    "image": "openshift/hello-openshift",
                    "ports": [
                        {
                            "containerPort": 8080,
                            "protocol": "TCP"
                        }
                    ],
                    "resources": {},
                    "volumeMounts": [
                        {
                            "name": "tmp",
                            "mountPath": "/tmp"
                        }
                    ],
                    "terminationMessagePath": "/dev/termination-log",
                    "imagePullPolicy": "IfNotPresent",
                    "capabilities": {},
                    "securityContext": {
                        "capabilities": {},
                        "privileged": False
                    }
                }
            ],
            "volumes": [
                {
                    "name": "tmp",
                    "emptyDir": {}
                }
            ],
            "restartPolicy": "Always",
            "dnsPolicy": "ClusterFirst",
            "serviceAccount": ""
        },
        "status": {}
    }
    payload = kwargs.get('payload', payload_default)
    return pod.create(provider.mgmt, payload=payload)


def gen_mgmt_service(provider, **kwargs):
    """Generate a Pod resource on a given provider using wrapanapi"""
    service_name = kwargs.get('service_name', 'some-test-service')
    service_namespace = kwargs.get('service_namespace', 'default')
    service = Service(provider.mgmt, service_name, service_namespace)
    payload_default = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {
            "name": service.name,
            "namespace": service.namespace
        },
        "spec": {
            "selector": {
                "name": service.name
            },
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 8888,
                    "targetPort": 8080
                }
            ]
        }
    }
    payload = kwargs.get('payload', payload_default)
    return service.create(provider.mgmt, payload=payload)


def gen_mgmt_node(provider, **kwargs):
    """Generate a Node resource on a given provider using wrapanapi"""
    node_fqdn = kwargs.get('node_fqdn', 'openshift-node.test.com')
    return Node(provider.mgmt, node_fqdn)


def gen_mgmt_replicator(provider, **kwargs):
    """Generate a Replicator resource on a given provider using wrapanapi"""
    replicator_name = kwargs.get('replicator_name', 'some-test-replicator')
    replicator_namespace = kwargs.get('replicator_namespace', 'default')
    replicator = Replicator(provider.mgmt, replicator_name, replicator_namespace)
    payload_default = {
        "kind": "ReplicationController",
        "apiVersion": "v1",
        "metadata": {
            "name": replicator.name,
            "namespace": replicator.namespace
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "app": "nginx"
            },
            "template": {
                "metadata": {
                    "name": replicator.name,
                    "labels": {
                        "app": 'nginx'
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": replicator.name,
                            "image": 'nginx',
                            "ports": [
                                {
                                    "containerPort": 80
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    payload = kwargs.get('payload', payload_default)
    return replicator.create(provider.mgmt, payload=payload)


def gen_mgmt_route(provider, **kwargs):
    """Generate a Route resource on a given provider using wrapanapi"""
    route_name = kwargs.get('route_name', 'some.test.route.com')
    route_namespace = kwargs.get('route_namespace', 'default')
    route = Route(provider.mgmt, route_name, route_namespace)
    service_name = kwargs.get('service_name', 'some-test-service')
    service_namespace = kwargs.get('service_namespace', 'default')
    service = Service(provider.mgmt, service_name, service_namespace)
    payload_default = {
        "metadata": {
            "name": "route-to-{}".format(service.name),
            "namespace": service.namespace
        },
        "spec": {
            "host": "www.example.com",
            "to": {
                "Kind": service.kind(),
                "name": service.name
            }
        }
    }
    payload = kwargs.get('payload', payload_default)
    return route.create(provider.mgmt, payload=payload)


def gen_mgmt_volume(provider, **kwargs):
    """Generate a Route resource on a given provider using wrapanapi"""
    volume_name = kwargs.get('volume_name', 'my-test-persistent-volume')
    volume = Volume(provider.mgmt, volume_name)
    payload_default = {
        "metadata": {"name": volume.name},
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "capacity": {"storage": "1Gi"},
            "nfs": {
                "path": "/tmp",
                "server": "12.34.56.78"
            }
        },
        "persistentVolumeReclaimPolicy": "Retain"
    }
    payload = kwargs.get('payload', payload_default)
    return volume.create(provider.mgmt, payload=payload)


def gen_mgmt_image_registry(provider, **kwargs):
    """Generate a Image Registry resource on a given provider using wrapanapi"""
    image_name = kwargs.get('image_name', 'openshift-hello-openshift')
    image_registry = kwargs.get('image_registry', 'docker.io/openshift/hello-openshift')
    registry_namespace = kwargs.get('registry_namespace', 'default')
    return ImageRegistry(provider.mgmt, image_name,
                         image_registry, registry_namespace)


def gen_mgmt_template(provider, **kwargs):
    template_name = kwargs.get('template_name', 'some-test-template')
    template_namespace = kwargs.get('template_namespace', 'default')
    template = Template(provider.mgmt, template_name, template_namespace)
    payload_default = {
        "apiVersion": "v1",
        "kind": "Template",
        "metadata": {
            "name": template.name,
            "annotations": {
                "description": "Description",
                "iconClass": "icon-redis",
                "tags": "database,nosql"
            },
            "namespace": template.namespace
        },
        "objects": [
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": "redis-master"
                },
                "spec": {
                    "containers": [
                        {
                            "env": [
                                {
                                    "name": "REDIS_PASSWORD",
                                    "value": "${REDIS_PASSWORD}"
                                }
                            ],
                            "image": "dockerfile/redis",
                            "name": "master",
                            "ports": [
                                {
                                    "containerPort": 6379,
                                    "protocol": "TCP"
                                }
                            ]
                        }
                    ]
                }
            }
        ],
        "parameters": [
            {
                "description": "Password used for Redis authentication",
                "from": "[A-Z0-9]{8}",
                "generate": "expression",
                "name": "REDIS_PASSWORD"
            }
        ],
        "labels": {
            "redis": "master"
        }
    }
    payload = kwargs.get('payload', payload_default)
    return template.create(provider.mgmt, payload=payload)
