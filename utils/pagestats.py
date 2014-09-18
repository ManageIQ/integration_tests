"""Object that represents page statistics and a list of any associated slow queries.

"""


class PageStat(object):

    def __init__(self):
        self.headers = ['request', 'status', 'transactiontime', 'completedintime', 'viewstime',
            'activerecordtime', 'selectcount', 'cachecount']
        self.request = ''
        self.status = ''
        self.transactiontime = 0
        self.completedintime = 0
        self.viewstime = 0
        self.activerecordtime = 0
        self.selectcount = 0
        self.cachecount = 0
        self.slowselects = []

    def __iter__(self):
        for header in self.headers:
            yield header, getattr(self, header)

    def __str__(self):
        return 'Transaction/Completed/Views/ActiveRecord:' + str(self.transactiontime).rjust(6) + \
            ':' + str(self.completedintime).rjust(8) + ':' + str(self.viewstime).rjust(8) + ':' + \
            str(self.activerecordtime).rjust(8) + ' Select/Cached: ' + \
            str(self.selectcount).rjust(5) + ':' + str(self.cachecount).rjust(5) + ', Request: ' + \
            self.request + ', Status: ' + self.status
