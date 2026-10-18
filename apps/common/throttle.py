"""Brute-force protection: lock a login target after too many FAILED attempts in a time window."""
from django.core.cache import cache
from rest_framework.exceptions import Throttled


class AttemptLimiter:
    """
    limiter = AttemptLimiter('pin', limit=5, window=300)
    limiter.check(key)   # raises 429 once `limit` failures were recorded (even if the next try is correct)
    limiter.fail(key)    # record a wrong attempt
    limiter.reset(key)   # clear after a successful login

    Counters live in Django's cache (per process by default; point CACHES at Redis/Memcached to share them
    between workers).
    """

    def __init__(self, scope, limit, window):
        self.scope, self.limit, self.window = scope, limit, window

    def _k(self, key):
        return f'attempts:{self.scope}:{key}'

    def check(self, key):
        if cache.get(self._k(key), 0) >= self.limit:
            raise Throttled(wait=self.window, detail='Too many wrong attempts. Please wait a few minutes and try again.')

    def fail(self, key):
        cache.add(self._k(key), 0, self.window)        # the window starts at the first failure
        try:
            cache.incr(self._k(key))
        except ValueError:                              # expired between add and incr
            cache.set(self._k(key), 1, self.window)

    def reset(self, key):
        cache.delete(self._k(key))


PIN_LIMITER = AttemptLimiter('pin', limit=5, window=300)           # 5 wrong PINs per person per terminal, 5 minutes
LOGIN_LIMITER = AttemptLimiter('login', limit=10, window=600)      # 10 wrong passwords per account, 10 minutes
