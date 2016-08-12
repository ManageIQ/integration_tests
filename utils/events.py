# -*- coding: utf-8 -*-

"""Library for event testing.

"""

from __future__ import unicode_literals
from cached_property import cached_property
from contextlib import contextmanager
from datetime import datetime


class EventTool(object):
    """EventTool serves as a wrapper to getting the events from the database.

    :var OBJECT_TABLE: Mapping of object types to tables and column names.
    """
    OBJECT_TABLE = {
        # target_type: (table_name, name_column, id_column)
        'VmOrTemplate': ('vms', 'name', 'id'),
        'Host': ('hosts', 'name', 'id'),
        'Service': ('services', 'name', 'id'),
    }

    def __init__(self, appliance):
        self.appliance = appliance

    @property
    def miq_event_definitions(self):
        """``miq_event_definitions`` table."""
        return self.appliance.db['miq_event_definitions']

    @property
    def event_streams(self):
        """``event_streams`` table."""
        return self.appliance.db['event_streams']

    def query(self, *args, **kwargs):
        """Wrapper for the SQLAlchemy query method."""
        return self.appliance.db.session.query(*args, **kwargs)

    @cached_property
    def all_event_types(self):
        """Returns a list of all possible events that can be used.

        Returns:
            A :py:class:`list` of :py:class:`str`.
        """
        return {q[0] for q in self.query(self.miq_event_definitions.name)}

    def process_id(self, target_type, target_id):
        """Resolves id, let it be a string or an id.

        In case the ``target_type`` is defined in the :py:const:`OBJECT_TABLE`, you can pass a
        string with object's name, otherwise a numeric id to the table is required.

        Args:
            target_type: What kind of object is the target of the event (MiqServer, VmOrTemplate...)
            target_id: An id or a name of the object.

        Returns:
            :py:class:`int` with id of the object in the database.
        """
        if isinstance(target_id, (int, long)):
            return target_id
        if target_type not in self.OBJECT_TABLE:
            raise TypeError(
                ('Type {} is not specified in the auto-coercion OBJECT_TABLE. '
                 'Pass a real id of the object or extend the table').format(target_type))
        table_name, name_column, id_column = self.OBJECT_TABLE[target_type]
        table = self.appliance.db[table_name]
        name_column = getattr(table, name_column)
        id_column = getattr(table, id_column)
        o = self.appliance.db.session.query(id_column).filter(name_column == target_id).first()
        if o is None:
            raise ValueError('{} with name {} not found.'.format(target_type, target_id))
        return o[0]

    def query_miq_events(
            self, target_type=None, target_id=None, event_type=None, since=None, until=None,
            from_id=None):
        """Checks whether an event occured.

        Args:
            target_type: What kind of object is the target of the event (MiqServer, VmOrTemplate)
            target_id: What is the ID of the object (or name, see :py:meth:`process_id`).
            event_type: Type of the event. Ideally one of the :py:meth:`all_event_types` but other
                kinds of events exist too.
            since: Since when you want to check it. UTC
            until: Until what time you want to check it.
        """
        until = until or datetime.utcnow()
        query = self.query(self.event_streams).filter(self.event_streams.type == 'MiqEvent')
        if target_type is not None:
            query = query.filter(self.event_streams.target_type == target_type)
        if target_id is not None:
            if target_type is None:
                raise TypeError('When specifying target_id you also must specify target_type')
            target_id = self.process_id(target_type, target_id)
            query = query.filter(self.event_streams.target_id == target_id)
        if event_type is not None:
            query = query.filter(self.event_streams.event_type == event_type)
        if since is not None:
            query = query.filter(self.event_streams.timestamp >= since)
        if until is not None:
            query = query.filter(self.event_streams.timestamp <= until)
        if from_id is not None:
            query = query.filter(self.event_streams.id > from_id)
        results = []
        for event in query:
            results.append({
                'id': event.id,
                'timestamp': event.timestamp,
                'message': event.message,
                'target_type': event.target_type,
                'target_id': event.target_id,
                'event_type': event.event_type})
        return results

    @contextmanager
    def ensure_event_happens(self, target_type, target_id, event_type):
        """Context manager usable for one-off checking of the events.

        See also: :py:meth:`query_miq_events`

        Args:
            target_type: What kind of object is the target of the event (MiqServer, VmOrTemplate)
            target_id: What is the ID of the object (or name, see :py:meth:`process_id`).
            event_type: Type of the event. Ideally one of the :py:meth:`all_event_types` but other
                kinds of events exist too.
        """
        time_started = datetime.utcnow()
        yield
        time_ended = datetime.utcnow()
        events = self.query_miq_events(target_type, target_id, event_type, time_started, time_ended)
        if len(events) == 0:
            raise AssertionError(
                'Event {}/{}/{} did not happen.'.format(event_type, target_type, target_id))
