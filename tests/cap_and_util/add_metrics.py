
import time
from unittestzero import Assert
import datetime
import db

def insert_previous_hour_raw_metric_data(db_session, resource_id, columns):
    resource_id = resource_id
    columns = columns
    date = datetime.datetime.utcnow()
    date = date.replace(microsecond=0)
    date = date.replace(second = 0)
    #date = date.replace(minute = 0)
    current_time = date
    date = date - datetime.timedelta(hours = 1)
    #previous_hour = date.hour
    capture_interval_name = 'realtime'
    session = db_session
    while date <= current_time:
        new_user = db.Metric(resource_id = resource_id)
        session.add(new_user)
        new_user.timestamp = date
        new_user.capture_interval_name = capture_interval_name
        date = date + datetime.timedelta(seconds = 20)
        for key, value in columns.items():
            setattr(new_user, key, value)
    session.commit()

def insert_previous_weeks_hourly_rollups(db_session, resource_id, columns):
    resource_id = resource_id                                                                      
    date=datetime.datetime.utcnow()
    capture_interval_name = 'hourly'
    date = date.replace(microsecond = 0)
    date = date.replace(second = 0)
    date = date.replace(minute = 0)
    date = date.replace(hour = 0)
    date = date - datetime.timedelta(days = 7)
    columns = columns                                                                         
    session = db_session                                                                                 
    for x in range(0, 168):                                                                         
        new_user = db.MetricRollup(resource_id = resource_id)
        session.add(new_user)
        new_user.timestamp = date
        new_user.capture_interval_name = capture_interval_name
        date = date + datetime.timedelta(hours = 1)
        for key, value in columns.items():
            setattr(new_user, key, value) 
    session.commit()    


def insert_previous_weeks_daily_rollups(db_session, resource_id, columns):
    resource_id = resource_id
    date=datetime.datetime.utcnow()
    capture_interval_name = 'daily'
    date = date.replace(microsecond = 0)
    date = date.replace(second = 0)
    date = date.replace(minute = 0)
    date = date.replace(hour = 0)
    date = date - datetime.timedelta(days = 7)
    columns = columns
    session = db_session
    for x in range(0, 7):
        new_user = db.MetricRollup(resource_id = resource_id)
        session.add(new_user)
        new_user.timestamp = date
        new_user.capture_interval_name = capture_interval_name
        date = date + datetime.timedelta(days = 1)
        for key, value in columns.items():
            setattr(new_user, key, value)
    session.commit()

