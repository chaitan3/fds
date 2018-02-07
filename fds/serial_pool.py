class Pool(object):
    def __init__(self, n):
        return

    def apply_async(self, f, args):
        res = PoolResult(f, args)
        return res

    def close(self):
        return

    def join(self):
        return

class PoolResult(object):
    def __init__(self, f, args):
        self.f = f
        self.args = args

    def get(self):
        return self.f(*self.args)
