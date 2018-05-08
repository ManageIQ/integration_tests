

def test_import_example():
    from ovirtsdk.api import API
    from ovirtsdk.infrastructure.errors import DisconnectedError, RequestError
    from ovirtsdk.xml import params