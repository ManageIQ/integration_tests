"""Library for event testing.
"""
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime
from numbers import Number
from threading import Event as ThreadEvent
from threading import Thread
from time import sleep

from cached_property import cached_property
from sqlalchemy.sql.expression import func

from cfme.utils.log import create_sublogger

logger = create_sublogger('events')


class EventTool:
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
        return self.appliance.db.client['miq_event_definitions']

    @property
    def event_streams(self):
        """``event_streams`` table."""
        return self.appliance.db.client['event_streams']

    @cached_property
    def event_streams_attributes(self):
        """``event_streams`` columns and python's column types"""
        self.appliance.db.client._table('event_streams')
        event_table = [tbl for tbl in self.appliance.db.client.metadata.sorted_tables
                       if tbl.name == 'event_streams'][-1]
        return [(cl.name, cl.type.python_type) for cl in event_table.c.values()]

    def query(self, *args, **kwargs):
        """Wrapper for the SQLAlchemy query method."""
        return self.appliance.db.client.session.query(*args, **kwargs)

    @cached_property
    def all_event_types(self):
        """Returns a list of all possible events that can be used.
        Returns:
            A :py:class:`list` of :py:class:`str`.
        """
        return {q[0] for q in self.query(self.miq_event_definitions.name)}

    def process_id(self, target_type, target_name):
        """Resolves id, let it be a string or an id.
        In case the ``target_type`` is defined in the :py:const:`OBJECT_TABLE`, you can pass a
        string with object's name, otherwise a numeric id to the table is required.
        Args:
            target_type: What kind of object is the target of the event (MiqServer, VmOrTemplate...)
            target_name: An id or a name of the object.
        Returns:
            :py:class:`int` with id of the object in the database.
        """
        if isinstance(target_name, Number):
            return target_name
        if target_type not in self.OBJECT_TABLE:
            raise TypeError(
                ('Type {} is not specified in the auto-coercion OBJECT_TABLE. '
                 'Pass a real id of the object or extend the table').format(target_type))
        table_name, name_column, id_column = self.OBJECT_TABLE[target_type]
        table = self.appliance.db.client[table_name]
        name_column = getattr(table, name_column)
        id_column = getattr(table, id_column)
        o = self.appliance.db.client.session.query(id_column).filter(
            name_column == target_name).first()
        if not o:
            raise ValueError(f'{target_type} with name {target_name} not found.')
        return o[0]

    def query_miq_events(self, target_type=None, target_id=None, event_type=None, since=None,
                         until=None, from_id=None):
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
        if target_type:
            query = query.filter(self.event_streams.target_type == target_type)
        if target_id:
            if not target_type:
                raise TypeError('When specifying target_id you also must specify target_type')
            target_id = self.process_id(target_type, target_id)
            query = query.filter(self.event_streams.target_id == target_id)
        if event_type:
            query = query.filter(self.event_streams.event_type == event_type)
        if since:
            query = query.filter(self.event_streams.timestamp >= since)
        if until:
            query = query.filter(self.event_streams.timestamp <= until)
        if from_id:
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
                f'Event {event_type}/{target_type}/{target_id} did not happen.')


class EventAttr:
    """
    contains one event attribute and the method for comparing it.
    """
    def __init__(self, attr_type=None, cmp_func=None, **attrs):
        if len(attrs) > 1:
            raise ValueError('event attribute can have only one key=value pair')

        self.name, self.value = list(attrs.items())[0]
        self.type = attr_type or type(self.value)
        self.cmp_func = cmp_func

    def match(self, attr):
        """
        compares current attribute with passed attribute
        """
        if not isinstance(attr, EventAttr) or self.name != attr.name:
            raise ValueError('Incorrect attribute is passed')

        if not attr.value or not self.value:
            return attr.value is None and self.value is None
        elif self.cmp_func:
            return self.cmp_func(self.value, attr.value)
        else:
            return self.value == attr.value

    def __repr__(self):
        return "{name}({type})={val}, cmp_func {cmp}".format(name=self.name, type=self.type,
                                                             val=self.value, cmp=self.cmp_func)


# fixme: would it be better to create event prototype and just clone it ?
class Event:
    """
    represents either db event received by CFME and stored in event_streams or an expected event
    """
    def __init__(self, event_tool, *args):
        self._tool = event_tool
        # filling obtaining default attributes and their types
        self._default_attrs = {}  # EventAttr obj
        self._populate_defaults()

        # container for event attributes
        self.event_attrs = {}  # EventAttr obj

        for arg in args:
            if isinstance(arg, EventAttr):
                self.add_attrs(arg)
            else:
                logger.warning(f"arg {arg} doesn't belong to EventAttr. ignoring it")

    def __repr__(self):
        params = ", ".join([f"{attr.name}={attr.value}"
                            for attr in
                            self.event_attrs.values()])
        return f"BaseEvent({params})"

    def _populate_defaults(self):
        for attr_name, attr_type in self._tool.event_streams_attributes:
            self._default_attrs[attr_name] = EventAttr(**{attr_name: None, 'attr_type': attr_type})

    def _parse_raw_event(self, evt):
        for attr in self._default_attrs:
            default_type = self._default_attrs[attr].type
            evt_value = getattr(evt, attr)
            evt_type = type(evt_value)
            # weird thing happens here. getattr sometimes takes value not equal to python_type
            # so, force type conversion has to be done
            if evt_value and evt_type is not default_type:
                evt_value = default_type(str(evt_value, 'utf8'))

            self.add_attrs(EventAttr(**{attr: evt_value}))

    def _is_raw_event(self, evt):
        return evt.__tablename__ == 'event_streams'

    def matches(self, evt):
        """
        compares current event with passed event.
        """
        if not isinstance(evt, type(self)):
            raise ValueError("passed event doesn't belong to {}".format(type(self)))

        # checking only common attributes
        if 'target_name' in self.event_attrs and 'target_id' not in self.event_attrs:
            try:
                target_id = self._tool.process_id(self.event_attrs['target_type'].value,
                                                  self.event_attrs['target_name'].value)
                self.event_attrs['target_id'] = EventAttr(**{'target_id': target_id})
            except ValueError:
                # vm or host name isn't added to db yet. need to wait
                return False

        common_attrs = set(self.event_attrs).intersection(set(evt.event_attrs))
        for attr in common_attrs:
            if not self.event_attrs[attr].match(evt.event_attrs[attr]):
                return False
        else:
            return True

    def add_attrs(self, *attrs):
        """
        event consists of attributes like event_type, etc.
        this method allows to add an attribute to event
        """
        if isinstance(attrs, Iterable):
            for attr in attrs:
                if attr.name == 'target_name':
                    # this is artificial attr which will be converted to target_id during matching
                    self.event_attrs[attr.name] = attr
                elif attr.name in self._default_attrs:
                    # type check was removed because sqlalchemy's python_type
                    # and type of returned values are different
                    self.event_attrs[attr.name] = attr
                else:
                    logger.warning('The attribute {} type {} is absent in DB '
                                   'or type mismatch.'.format(attr.name, attr.type))
        else:
            raise ValueError(f"incorrect parameters are passed {attrs}")
        return self

    def build_from_raw_event(self, evt):
        """
        helper method which takes raw event from event_streams and prepares event object
        """
        # checking is this param - raw event, populating fields by this data then
        if self._is_raw_event(evt):
            self._parse_raw_event(evt)
        return self


class DbEventListener(Thread):
    """
     accepts "expected" events, listens to db events and compares showed up events with expected
     events. Runs callback function if expected events have it.
    """
    def __init__(self, appliance):
        super().__init__()
        self._appliance = appliance
        self._tool = EventTool(self._appliance)

        self._events_to_listen = []
        # last_id is used to ignore already arrived messages the database
        # When database is "cleared" the id of the last event is placed here. That is then used
        # in queries to prevent events of this id and earlier to get in.
        self._last_processed_id = None
        self._stop_event = ThreadEvent()

    def set_last_record(self, evt=None):
        if evt:
            self._last_processed_id = evt.event_attrs['id'].value
        else:
            try:
                self._last_processed_id = self._tool.query(
                    func.max(self._tool.event_streams.id)).one()
            except IndexError:
                # No events yet, so do nothing
                pass

    def new_event(self, *attrs, **kwattrs):
        """
        this method just simplifies "expected" event creation.
        Usage:
            listener = appliance.event_listener()
            evt = listener.new_event(target_type='VmOrTemplate',
                                    target_name='my_lovely_vm',
                                    event_type='vm_create')
            listener.listen_to(evt)
        """
        event = Event(event_tool=self._tool)
        for name, value in kwattrs.items():
            event.add_attrs(EventAttr(**{name: value}))

        for attr in attrs:
            event.add_attrs(EventAttr(**attr))
        return event

    def listen_to(self, *evts, **kwargs):
        """
        accepts one or many events
        callback function will be called when event arrived in event_streams.
        callback will receive expected event and got event as params.

        Args:
            evts: list of events which EventListener should listen to
            callback: callback function that will be called if event is received
            first_event: EventListener waits for only first event of such type.
                         it ignores such event in future if first matching event is found.

        By default EventListener collects and receives all matching events.
        """
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None

        # if first_event = True, these expected events won't be checked after first match
        if 'first_event' in kwargs and kwargs['first_event']:
            first_event = True
        else:
            first_event = False

        if isinstance(evts, Iterable):
            for evt in evts:
                if isinstance(evt, Event):
                    logger.info(f"event {evt} is added to listening queue")
                    self._events_to_listen.append({'event': evt,
                                                   'callback': callback,
                                                   'matched_events': [],
                                                   'first_event': first_event})
                else:
                    raise ValueError("one of events doesn't belong to Event class")
        else:
            raise ValueError('incorrect is passed')

    def start(self):
        logger.info('Event Listener has been started')
        self.set_last_record()
        self._stop_event.clear()
        super().start()

    def stop(self):
        logger.info('Event Listener has been stopped')
        self._stop_event.set()

    def run(self):
        self.process_events()

    @property
    def started(self):
        return super().is_alive()

    def process_events(self):
        """
        processes all new db events and compares them with expected events.
        processed events are ignored next time
        """
        while not self._stop_event.is_set():
            events = self.get_next_portion()
            if len(events) == 0:
                sleep(0.2)
                continue
            for got_event in events:
                logger.debug(f"processing event id {got_event.id}")
                got_event = Event(event_tool=self._tool).build_from_raw_event(got_event)
                for exp_event in self._events_to_listen:
                    if exp_event['first_event'] and len(exp_event['matched_events']) > 0:
                        continue

                    if exp_event['event'].matches(got_event):
                        if exp_event['callback']:
                            exp_event['callback'](exp_event=exp_event['event'], got_event=got_event)
                        exp_event['matched_events'].append(got_event)
                self.set_last_record(got_event)

                if self._stop_event.is_set():
                    break

    @property
    def got_events(self):
        """
        returns dict with expected events and all the events matched to expected ones
        """
        evts = [(evt['event'], len(evt['matched_events'])) for evt in self._events_to_listen]
        logger.info(evts)
        return self._events_to_listen

    def reset_matches(self):
        for event in self._events_to_listen:
            event['matched_events'] = []

    def reset_events(self):
        self._events_to_listen = []

    def get_next_portion(self):
        logger.debug("obtaining next portion of events")
        return self._tool.query(self._tool.event_streams)\
            .filter(self._tool.event_streams.id > self._last_processed_id)\
            .order_by(self._tool.event_streams.id).yield_per(100).all()

    def check_expected_events(self):
        return all([len(event['matched_events']) for event in self.got_events])

    def __call__(self, *args, **kwargs):
        """
        it is called by register_event fixture.
        bad idea, to replace register_event by object later
        """
        if 'first_event' in kwargs:
            first_event = kwargs.pop('first_event')
        else:
            first_event = True
        evt = self.new_event(*args, **kwargs)
        logger.info(f"registering event: {evt}")
        self.listen_to(evt, callback=None, first_event=first_event)
