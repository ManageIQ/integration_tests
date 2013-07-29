import time                                                           
from unittestzero import Assert
import datetime                                                                                         
import db

def delete_raw_metric_data(db_session, resource_id):
    resource_id = resource_id
    session = db_session  
    session.query(db.Metric).filter(db.Metric.resource_id == resource_id).delete() 

    session.commit()

def delete_metric_rollup_data(db_session, resource_id):
    resource_id = resource_id
    session = db_session
    session.query(db.MetricRollup).filter(db.MetricRollup.resource_id == resource_id).delete()

    session.commit()


