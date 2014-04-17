def delete_raw_metric_data(db, resource_id):
    metrics = db['metrics']
    with db.transaction:
        db.session.query(metrics).filter(metrics.resource_id == resource_id).delete()


def delete_metric_rollup_data(db, resource_id):
    metric_rollups = db['metric_rollups']
    with db.transaction:
        db.session.query(metric_rollups).filter(metric_rollups.resource_id == resource_id).delete()
