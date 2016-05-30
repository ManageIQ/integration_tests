import re
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, paginator
from cfme.web_ui.menu import nav, toolbar as tb
from mgmtsystem.hawkular import Deployment, Path
from utils.db import cfmedb
from utils.varmeth import variable
from . import LIST_TABLE_LOCATOR, MiddlewareBase

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, server=None, provider=None):
    t_ms = cfmedb()['middleware_servers']
    t_md = cfmedb()['middleware_deployments']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_md.nativeid, t_md.name,
                                   t_md.ems_ref, t_ms.name, t_ems.name).join(t_ms,
                                            t_md.server_id == t_ms.id).join(t_ems,
                                            t_md.ems_id == t_ems.id)
    if name:
        query = query.filter(t_md.name == name)
    if server:
        query = query.filter(t_md.nativeid.like('%{}%'.format(server)))
    if provider:
        query = query.filter(t_ems.name == provider)
    return query

nav.add_branch(
    'middleware_deployments', {
        'middleware_deployment': lambda ctx: list_tbl.select_row('Deployment Name', ctx['name']),
        'middleware_deployment_detail':
            lambda ctx: list_tbl.click_row_by_cells({'Deployment Name': ctx['name']}),
    }
)


class MiddlewareDeployment(MiddlewareBase):
    """
    MiddlewareDeployment class provides details on deployment page.
    Class methods available to get existing deployments list

    Args:
        name: Name of the deployment
        provider: Provider object (HawkularProvider)
        id: Native id (internal id) of deployment
        server: Server name of the deployment

    Usage:

        mydeployment = MiddlewareDeployment(name='Foo.war',
                                server='Bar-serv',
                                provider=haw_provider)

        deployments = MiddlewareDeployment.deployments()

    """
    property_tuples = [('name', 'name')]

    def __init__(self, name, provider=None, **kwargs):
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.provider = provider
        self.id = kwargs['id'] if 'id' in kwargs else None
        self.server = kwargs['server'] if 'server' in kwargs else None

    @classmethod
    def deployments(cls, provider=None):
        deployments = []
        if provider:
            # if provider instance is provided try to navigate provider's deployments page
            # if no deployments are registered in provider, returns empty list
            if not provider.load_all_provider_deployments():
                return []
        else:
            # if provider instance is not provided then navigates  to all deployments page
            sel.force_navigate('middleware_deployments')
        if sel.is_displayed(list_tbl):
            for page in paginator.pages():
                for row in list_tbl.rows():
                    deployments.append(MiddlewareDeployment(name=row.deployment_name.text,
                                                            server=row.server.text))
        return deployments

    @classmethod
    def deployments_in_db(cls, server=None, provider=None):
        deployments = []
        rows = _db_select_query(server=server, provider=(provider.name if provider else None)).all()
        for deployment in rows:
            deployments.append(MiddlewareDeployment(id=deployment[0], name=deployment[1],
                                                    server=deployment[3], provider=deployment[4]))
        return deployments

    @classmethod
    def deployments_in_mgmt(cls, provider):
        deployments = []
        rows = provider.mgmt.list_server_deployment()
        for deployment in rows:
            deployments.append(MiddlewareDeployment(provider=provider.name,
                    id=deployment.id, name=deployment.name,
                    server=re.sub(r'~~$', '', deployment.path.resource[0])))
        return deployments

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            sel.force_navigate('middleware_deployment_detail', context={'name': self.name})
        if refresh:
            tb.refresh()

    @variable(alias='ui')
    def deployment(self):
        self.summary.reload()
        if self.summary.properties:
            return Deployment(name=self.summary.properties.name.text_value,
                              id=self.summary.properties.nativeid.text_value, path=None)
        return None

    @deployment.variant('mgmt')
    def deployment_in_mgmt(self):
        raise NotImplementedError('This feature not implemented yet')

    @deployment.variant('db')
    def deployment_in_db(self):
        if self.name:
            deployment = _db_select_query(self.name, self.server).first()
            if deployment:
                return Deployment(deployment[0], deployment[1], Path(deployment[2]))
            return None
        raise KeyError('Variable "name" not set!')

    @deployment.variant('rest')
    def deployment_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')
