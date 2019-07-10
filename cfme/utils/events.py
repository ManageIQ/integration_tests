# -*- coding: utf-8 -*-
"""Library for event testing.

"""
from threading import Event as ThreadEvent
from threading import Thread
from time import sleep

from manageiq_client.filters import Q

from cfme.utils.log import create_sublogger

logger = create_sublogger('events')


class EventAttr(object):
    """ EventAttr helps to compare event attributes with specific method.

    Contains one event attribute and the method for comparing it.
    """
    def __init__(self, attr_type=None, cmp_func=None, **attrs):
        if len(attrs) > 1:
            raise ValueError('event attribute can have only one key=value pair')

        self.name, self.value = list(attrs.items())[0]
        self.type = attr_type or type(self.value)
        self.cmp_func = cmp_func

    def match(self, attr):
        """ Compares current attribute with passed attribute."""
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


class Event(object):
    """ Event represents either event received by REST API or an expected event.

    :var TARGET_TYPES: Mapping of object types to REST API collections.
    """
    TARGET_TYPES = {
        # target_type: target_rest
        'VmOrTemplate': 'vms',
        'Host': 'hosts',
        'Service': 'services',
    }

    def __init__(self, appliance, *args):
        self._appliance = appliance
        self.event_attrs = {}  # container for EventAttr objects

        for arg in args:
            if isinstance(arg, EventAttr):
                self.add_attrs(arg)
            else:
                logger.warning("arg {} doesn't belong to EventAttr. ignoring it".format(arg))

    def __repr__(self):
        params = ", ".join(["{}={}".format(attr.name, attr.value)
                            for attr in
                            self.event_attrs.values()])
        return "BaseEvent({})".format(params)

    def process_id(self):
        """ Resolves target_id by target_type and target name."""
        if 'target_name' in self.event_attrs and 'target_id' not in self.event_attrs:
            try:
                target_type = self.event_attrs['target_type'].value
                target_name = self.event_attrs['target_name'].value

                # Target type should be present in TARGET_TYPES
                if target_type not in self.TARGET_TYPES:
                    raise TypeError(
                        'Type {} is not specified in the TARGET_TYPES.'.format(target_type))

                target_rest = self.TARGET_TYPES[target_type]
                target_collection = getattr(self._appliance.rest_api.collections, target_rest)
                o = target_collection.filter(Q('name', '=', target_name))

                if not o.resources:
                    raise ValueError('{} with name {} not found.'.format(target_type, target_name))

                # Set target_id if target object was found
                self.event_attrs['target_id'] = EventAttr(**{'target_id': o[0].id})

            except ValueError:
                # Target isn't added yet. Need to wait
                sleep(1)

    def matches(self, evt):
        """ Compares common attributes of expected event and passed event."""
        common_attrs = set(self.event_attrs).intersection(set(evt.event_attrs))
        for attr in common_attrs:
            if not self.event_attrs[attr].match(evt.event_attrs[attr]):
                return False
        else:
            return True

    def add_attrs(self, *attrs):
        """ Adds an EventAttr to event."""
        for attr in attrs:
            self.event_attrs[attr.name] = attr
        return self

    def build_from_entity(self, event_entity):
        """ Builds Event object from event Entity"""
        for key, value in event_entity['_data'].items():
            self.add_attrs(EventAttr(**{key: value}))
        return self


class RestEventListener(Thread):
    """ EventListener accepts "expected" events, listens to db events and compares matched events
    with expected events. Runs callback function if expected events have it.

    :var FILTER_ATTRS: List of filters used in REST API call
    """
    FILTER_ATTRS = ['event_type', 'target_type', 'target_id', 'source']

    def __init__(self, appliance):
        super(RestEventListener, self).__init__()
        self._appliance = appliance
        self._events_to_listen = []
        self._last_processed_id = 0  # this is used to filter out old or processed events
        self._stop_event = ThreadEvent()

        self.event_streams = appliance.rest_api.collections.event_streams

    def get_max_record_id(self):
        try:
            return self.event_streams.query_string(limit=1, sort_order='desc', sort_by='id')[0].id
        except IndexError:
            return None

    def new_event(self, *attrs, **kwattrs):
        """ This method simplifies "expected" event creation.

        Usage:
            listener = appliance.event_listener()
            evt = listener.new_event(target_type='VmOrTemplate',
                                     target_name='my_lovely_vm',
                                     event_type='vm_create')
            listener.listen_to(evt)
        """
        event = Event(self._appliance)
        for name, value in kwattrs.items():
            event.add_attrs(EventAttr(**{name: value}))

        for attr in attrs:
            event.add_attrs(EventAttr(**attr))
        return event

    def listen_to(self, *evts, **kwargs):
        """ Adds expected events to EventListener

        May accept one or many events.
        Callback function will is called when expected event has arrived in event_streams.
        Callback will receive expected event and got event as params.

        Args:
            evts: list of events which EventListener should listen to
            callback: callback function that will be called if event is received
            first_event: EventListener will skip processing event if it has been occurred once.

        By default EventListener collects and receives all matching events.
        """
        callback = kwargs.get('callback')
        first_event = bool(kwargs.get('first_event'))

        for evt in evts:
            if isinstance(evt, Event):
                exp_event = {'event': evt,
                             'callback': callback,
                             'matched_events': [],
                             'first_event': first_event}
                self._events_to_listen.append(exp_event)
                logger.info("event {} is added to listening queue.".format(evt))
            else:
                raise ValueError("one of events doesn't belong to Event class")

    def start(self):
        self._last_processed_id = self.get_max_record_id()
        self._stop_event.clear()
        super(RestEventListener, self).start()
        logger.info('Event Listener has been started')

    def stop(self):
        self._stop_event.set()
        logger.info('Event Listener has been stopped')

    @property
    def started(self):
        return super(RestEventListener, self).is_alive()

    def run(self):
        """ Overrides ThreadEvent run to continuously process events"""
        self.process_events()

    def process_events(self):
        """ Processes all new events and compares them with expected events.

        Processed events are ignored next time.
        """
        while not self._stop_event.is_set():
            sleep(1)
            cur_last_record_id = self.get_max_record_id()
            if not cur_last_record_id:
                continue

            for exp_event in self._events_to_listen:

                # Skip if event has occurred
                if exp_event['first_event'] and len(exp_event['matched_events']):
                    continue

                matched_events = self.get_next_portion(exp_event['event'], cur_last_record_id)

                if not matched_events:
                    continue

                # Match events
                try:
                    for event_entity in matched_events:
                        got_event = Event(self._appliance).build_from_entity(event_entity)
                        if exp_event['event'].matches(got_event):
                            if exp_event['callback']:
                                exp_event['callback'](exp_event=exp_event['event'],
                                                      got_event=got_event)
                            exp_event['matched_events'].append(got_event)
                except Exception:
                    logger.exception("An exception during matching events occurred.")

                if self._stop_event.is_set():
                    break
            self._last_processed_id = cur_last_record_id

    def get_next_portion(self, evt, max_id=None):
        """ Returns list with one or more events matched with expected event.

        Returns None if there is no matched events."""
        evt.process_id()

        q = Q('id', '>', self._last_processed_id)  # ensure we get only new events
        if max_id:
            q &= Q('id', '<=', max_id)

        used_filters = set(self.FILTER_ATTRS).intersection(set(evt.event_attrs))
        for filter_attr in used_filters:
            evt_attr = evt.event_attrs[filter_attr]
            if evt_attr.value:
                q &= Q(filter_attr, '=', evt_attr.value)
        result = self.event_streams.filter(q)

        if len(result):
            return result

    @property
    def got_events(self):
        """ Returns dict with expected events and all the events matched to expected ones."""
        evts = [(evt['event'], len(evt['matched_events'])) for evt in self._events_to_listen]
        logger.info(evts)
        return self._events_to_listen

    def reset_events(self):
        self._events_to_listen = []

    def check_expected_events(self):
        """ Checks that all expected events has arrived."""
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
        logger.info("registering event: {}".format(evt))
        self.listen_to(evt, callback=None, first_event=first_event)
