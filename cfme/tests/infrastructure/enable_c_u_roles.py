from cfme.configure.configuration import server_roles_enabled


def enable_c_u_roles():
    with server_roles_enabled('ems_metrics_collector',
                              'ems_metrics_coordinator',
                              'ems_metrics_processor', 'smartproxy'):
        assert "Server C&U Enabled"
