import attr
import re
from datetime import datetime

from cfme.utils.appliance import current_appliance
from cfme.modeling.base import (
    BaseCollection,
    BaseEntity)


def _db_select_query(server):
    """column order: `id`, `queued_at`, `requesting_user`, `status`"""
    t_ms = current_appliance.db.client['middleware_servers']
    t_mdr = current_appliance.db.client['middleware_diagnostic_reports']
    query = current_appliance.db.client.session.query(
        t_mdr.id,
        t_mdr.queued_at,
        t_mdr.requesting_user.label('username'),
        t_mdr.status).join(t_mdr, t_mdr.middleware_server_id == t_ms.id)
    if server:
        query = query.filter(t_ms.name == server.name)
    return query


@attr.s
class JDRReport(BaseEntity):
    """ JDRReport class provides actions and details of JDR Reports List

    JDRReport class provides actions and details of JDR Reports List
    on Middleware Server page.
    Class method available to get existing JDR list for provided Server

    Args:
        server: Server for which report is generated
        username: user queued the JDR Report
        status: status of the JDR Report
        filename: name of the JDR Report file
        size: size of the JDR Report file
        queued_at: queued time of the JDR Report
        db_id: database row id of JDR Report
    """

    pretty_attrs = ['server', 'username', 'status', 'filename', 'size', 'queued_at', 'db_id']

    server = attr.ib()
    username = attr.ib()
    status = attr.ib()
    filename = attr.ib()
    size = attr.ib()
    queued_at = attr.ib()
    db_id = attr.ib()

    def delete(self):
        """ Deletes the JDR Report """
        raise NotImplementedError

    def download(self):
        """ Downloads the JDR Report """
        raise NotImplementedError


@attr.s
class JDRReportCollection(BaseCollection):
    """Collection class for `cfme.middleware.jdr_report.JDRReport`"""
    ENTITY = JDRReport

    def __init__(self, appliance, parent):
        self.appliance = appliance
        self.parent = parent

    def all(self):
        """Return all JDR Reports of the appliance.

        Returns: a :py:class:`list` of :py:class:`cfme.middleware.jdr_report.JDRReport` instances
        """
        reports = []
        view = self.parent.load_details(refresh=True)
        if view.jdr_reports.table:
            for row in view.jdr_reports.table:
                reports.append(self.instantiate(
                    self.appliance,
                    row.username.text,
                    row.status.text,
                    row.filename.text,
                    row.size.text,
                    row.queued_at.text,
                    None))
        return reports

    def headers(self):
        view = self.parent.load_details(refresh=True)
        if view.jdr_reports.entities:
            headers = [hdr.encode("utf-8")
                       for hdr in view.entities.elements.headers if hdr]
        return headers

    def all_in_db(self):
        reports = []
        rows = _db_select_query(server=self.parent).all()
        for report in rows:
            reports.append(self.instantiate(
                self.appliance,
                report.username,
                report.status,
                None,
                None,
                report.queued_at,
                report.id))
        return reports

    def contains_report(self, date_after=datetime.min):
        reports = self.all()
        for report in reports:
            if datetime.strptime(
                    report.queued_at, '%Y-%m-%d %H:%M:%S %Z') >= date_after:
                return True
        return False

    def report_ready(self, date_after=datetime.min):
        reports = self.all()
        for report in reports:
            if report.status == 'Ready' and self._queued_after(report, date_after):
                return True
        return False

    def report_queued(self, date_after=datetime.min):
        reports = self.all()
        for report in reports:
            if report.status == 'Queued' and self._queued_after(report, date_after):
                return True
        return False

    def report_running(self, date_after=datetime.min):
        reports = self.all()
        for report in reports:
            if report.status == 'Running' and self._queued_after(report, date_after):
                return True
        return False

    def _queued_after(self, report, date_after):
        return datetime.strptime(
            re.sub(r' \+\d+', '', report.queued_at), '%a, %d %b %Y %H:%M:%S') >= date_after
