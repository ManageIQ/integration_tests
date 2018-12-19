def test_auth_attributes_of_nuage_ae_class(appliance):
    """
        Ensure Nuage AE Class contains auth attributes in AE Schema
    """
    expected_fields = ['nuage_password', 'nuage_username', 'nuage_enterprise', 'nuage_url',
                       'nuage_api_version']
    manageiq_domain = appliance.collections.domains.instantiate(name='ManageIQ')
    system_namespace = manageiq_domain.namespaces.instantiate(name='System')
    event_namespace = system_namespace.namespaces.instantiate(name='Event')
    ems_event_namespace = event_namespace.namespaces.instantiate(name='EmsEvent')
    nuage_class = ems_event_namespace.classes.instantiate(name='Nuage')
    schema_fields = nuage_class.schema.schema_field_names

    assert all(expected in schema_fields for expected in expected_fields)
