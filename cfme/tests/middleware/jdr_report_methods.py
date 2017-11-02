from cfme.utils.wait import wait_for

DELAY = 30
NUM_SECS = 300


def verify_report_queued(jdr_rc, date_after):
    wait_for(lambda: jdr_rc.report_queued(date_after=date_after),
             delay=DELAY, num_sec=NUM_SECS,
             message='JDR Report must be found Queued after {}'
             .format(date_after))


def verify_report_ready(jdr_rc, date_after):
    wait_for(lambda: jdr_rc.report_ready(date_after=date_after),
             delay=DELAY, num_sec=NUM_SECS,
             message='JDR Report must be found Ready after {}'
             .format(date_after))


def verify_report_running(jdr_rc, date_after):
    wait_for(lambda: jdr_rc.report_running(date_after=date_after),
             delay=DELAY, num_sec=NUM_SECS,
             message='JDR Report must be found Running after {}'
             .format(date_after))


def verify_report_deleted(jdr_rc, date_after):
    wait_for(lambda: not jdr_rc.contains_report(date_after=date_after),
             delay=DELAY, num_sec=NUM_SECS,
             message='JDR Report must not exist after {}'
             .format(date_after))
