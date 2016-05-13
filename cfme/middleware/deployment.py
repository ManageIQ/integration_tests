from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable
from cfme.web_ui.menu import nav, toolbar as tb
from mgmtsystem.hawkular import Deployment, Path
from utils.db import cfmedb
from utils.varmeth import variable
from . import LIST_TABLE_LOCATOR, MiddlewareBase

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, server=None):
    t_md = cfmedb()['middleware_deployments']
    query = cfmedb().session.query(t_md.nativeid, t_md.name, t_md.ems_ref)
    if name:
        query = query.filter(t_md.name == name)
    if server:
        query = query.filter(t_md.nativeid.like('%{}%'.format(server)))
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
    def deployments(cls, provider):
        sel.force_navigate('middleware_deployments')
        deployments = []
        for row in list_tbl.rows():
            deployments.append(MiddlewareDeployment(
                provider=provider, name=row.deployment_name.text, server=row.server.text))
        return deployments

    @classmethod
    def deployments_in_db(cls, server=None):
        deployments = []
        rows = _db_select_query(server=server).all()
        for deployment in rows:
            deployments.append(Deployment(deployment[0], deployment[1], Path(deployment[2])))
        return deployments

    @classmethod
    def deployments_in_mgmt(cls, provider):
        return provider.mgmt.list_server_deployment()

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
