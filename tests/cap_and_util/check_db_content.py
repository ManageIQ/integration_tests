import db


def check_off_hours(db_session, resource_name, columns, timestamp):
    columns = columns
    timestamp = timestamp
    session = db_session
    resource_name = resource_name

    entry = session.query(db.MetricRollup).filter(
        db.MetricRollup.resource_name == resource_name,
        db.MetricRollup.timestamp == timestamp,
        db.MetricRollup.capture_interval_name == 'hourly').first()
    if entry is None:
        #pytest.set_trace()
        return 'missing'

    i = 0

    while(i < len(columns)):
        #pytest.set_trace()
        tmp_value = getattr(entry, columns[i])
        if tmp_value is not None and tmp_value != 0:
            #pytest.set_trace()
            return 'incorrect_off_data'
        i += 1


def check_on_hours(db_session, resource_name, columns, timestamp):
    columns = columns
    timestamp = timestamp
    session = db_session
    resource_name = resource_name

    entry = session.query(db.MetricRollup).filter(
        db.MetricRollup.resource_name == resource_name,
        db.MetricRollup.timestamp == timestamp).first()
    if entry is None:
        #pytest.set_trace()
        return 'missing'
    i = 0
    while(i < len(columns)):
        #pytest.set_trace()
        tmp_value = getattr(entry, columns[i])
        if tmp_value is None:
            return 'incorrect_on_data'
        i += 1
