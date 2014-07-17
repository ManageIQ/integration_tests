from utils.randomness import generate_random_string
from cfme.automate.explorer import Namespace, Class, Instance, Domain
from utils import version


@version.dependent
def a_domain():
    return None


@a_domain.method('5.3')
def a_domain_53():
    return Domain(name=generate_random_string(8),
                  description=generate_random_string(32),
                  enabled=True)


def make_domain():
    d = a_domain()
    if d:
        d.create()
    return d


def a_namespace(domain=None):
    if not domain:
        domain = make_domain()
    return Namespace(name=generate_random_string(8),
                     description=generate_random_string(32),
                     parent=domain)


def a_namespace_with_path(domain=None):
    name = generate_random_string(8)
    if not domain:
        domain = make_domain()

    n = Namespace.make_path('Factory', 'StateMachines', name, domain=domain)
    n.description = generate_random_string(32)
    return n


def make_namespace():
    ns = a_namespace()
    ns.create()
    return ns


def a_class(ns=None):
    if not ns:
        ns = make_namespace()
    return Class(name=generate_random_string(8),
                 description=generate_random_string(32),
                 namespace=ns)


def make_class(ns=None):
    cls = a_class(ns)
    cls.create()
    return cls


def an_instance(cls=None):
    if not cls:
        cls = make_class()
    return Instance(name=generate_random_string(8),
                    description=generate_random_string(32),
                    cls=cls)
