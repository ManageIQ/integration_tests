from multiprocessing.pool import CLOSE, Pool

class ResultsPool(Pool):
    """multiprocessing.Pool boilerplate wrapper

- Stores results on a results property
- Task result successes are aggregated by the sucessful property

"""
    def __init__(self, *args, **kwargs):
        super(ResultsPool, self).__init__(*args, **kwargs)

    def apply_async(self, *args, **kwargs):
        result = super(ResultsPool, self).apply_async(*args, **kwargs)
        self.results.append(result)
        return result

    def map_async(self, *args, **kwargs):
        result = super(ResultsPool, self).map_async(*args, **kwargs)
        self.results.append(result)
        return result

    @property
    def successful(self):
        if self.results:
            return all([result.successful() for result in self.results])
        else:
            return None

    def __enter__(self):
        self.results = list()
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
        self.join()
