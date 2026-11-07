"""Core memoisation implementation for mini-memoize.

The library provides a bounded memoisation decorator with a custom key
function.  The key function is responsible for turning the positional and
keyword arguments of a call into a hashable key.  A bounded store is used
so that a long-running process cannot grow without limit; when the store is
full the least-recently-used entry is evicted.

This module intentionally avoids third-party dependencies and uses only the
standard library.  The implementation is deliberately small and focused on
correctness for the common cases.
"""

from __future__ import annotations

from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Optional, Tuple


class MemoizedFunction:
    """A callable wrapper that caches results of a single function.

    The wrapper stores a bounded mapping from keys to results.  The key for
    a call is produced by ``key_func(*args, **kwargs)``.  If ``key_func``
    raises, the exception propagates and nothing is cached.

    Access to the cache is not thread-safe.  If you need thread safety,
    wrap calls to the memoized function in your own lock.  This choice keeps
    the implementation simple and avoids the overhead of locking for the
    common single-threaded case.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        key_func: Callable[..., Any],
        maxsize: Optional[int] = 128,
    ) -> None:
        if maxsize is not None and maxsize <= 0:
            raise ValueError("maxsize must be a positive integer or None")
        if not callable(func):
            raise TypeError("func must be callable")
        if not callable(key_func):
            raise TypeError("key_func must be callable")

        self._func = func
        self._key_func = key_func
        self._maxsize = maxsize
        # OrderedDict is used so that the least-recently-used entry can be
        # evicted in O(1) time.  A plain dict would require a separate
        # structure to track recency.
        self._cache: "OrderedDict[Any, Any]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Preserve the wrapped function's metadata.  This matters for
        # introspection tools and for debugging.
        wraps(func)(self)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        key = self._key_func(*args, **kwargs)

        try:
            result = self._cache[key]
        except KeyError:
            self._misses += 1
            result = self._func(*args, **kwargs)
            # Store the result.  If the store is bounded and full, evict
            # the least-recently-used entry before inserting.
            if self._maxsize is not None and len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
                self._evictions += 1
            self._cache[key] = result
        else:
            self._hits += 1
            # Move the key to the end to mark it as recently used.
            self._cache.move_to_end(key)

        return result

    def cache_clear(self) -> None:
        """Remove all cached entries and reset statistics."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def cache_info(self) -> Tuple[int, int, int, int, Optional[int]]:
        """Return ``(hits, misses, evictions, size, maxsize)``."""
        return (
            self._hits,
            self._misses,
            self._evictions,
            len(self._cache),
            self._maxsize,
        )

    def __wrapped__(self) -> Callable[..., Any]:
        """The original undecorated function."""
        return self._func


def memoize(
    key_func: Optional[Callable[..., Any]] = None,
    maxsize: Optional[int] = 128,
) -> Callable[[Callable[..., Any]], MemoizedFunction]:
    """Decorator that caches calls to the wrapped function.

    ``key_func`` must be a callable that accepts the same arguments as the
    decorated function and returns a hashable value.  If ``key_func`` is
    ``None``, a default key function is used that combines positional and
    keyword arguments into a tuple.  Keyword arguments are sorted by name so
    that calls with the same keyword arguments in a different order produce
    the same key.

    ``maxsize`` bounds the number of cached entries.  When the cache is
    full, the least-recently-used entry is evicted.  Pass ``None`` for an
    unbounded cache.
    """

    if key_func is None:
        def key_func(*args: Any, **kwargs: Any) -> Tuple[Tuple[Any, ...], Tuple[Tuple[str, Any], ...]]:
            # Sorting keyword items makes the key independent of the order
            # in which keywords were passed, which is what callers expect.
            return (args, tuple(sorted(kwargs.items())))

    if not callable(key_func):
        raise TypeError("key_func must be callable")

    def decorator(func: Callable[..., Any]) -> MemoizedFunction:
        return MemoizedFunction(func, key_func, maxsize)

    return decorator
