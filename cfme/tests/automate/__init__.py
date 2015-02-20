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


def make_domain(request=None):
    d = a_domain()
    if d:
        d.create()
        if request is not None:
            request.addfinalizer(d.delete)
    return d


def a_namespace(domain=None, request=None):
    if not domain:
        domain = make_domain(request=request)
    return Namespace(name=generate_random_string(8),
                     description=generate_random_string(32),
                     parent=domain)


def a_namespace_with_path(domain=None, request=None):
    name = generate_random_string(8)
    if not domain:
        domain = make_domain(request=request)

    n = Namespace.make_path('Factory', 'StateMachines', name, domain=domain)
    n.description = generate_random_string(32)
    return n


def make_namespace(request=None):
    ns = a_namespace(request=request)
    ns.create()
    if request is not None:
        request.addfinalizer(ns.delete)
    return ns


def a_class(ns=None, request=None):
    if not ns:
        ns = make_namespace(request=request)
    return Class(name=generate_random_string(8),
                 description=generate_random_string(32),
                 namespace=ns)


def make_class(ns=None, request=None):
    cls = a_class(ns, request=request)
    cls.create()
    if request is not None:
        request.addfinalizer(cls.delete)
    return cls


def an_instance(cls=None, request=None):
    if not cls:
        cls = make_class(request=request)
    return Instance(name=generate_random_string(8),
                    description=generate_random_string(32),
                    cls=cls)
