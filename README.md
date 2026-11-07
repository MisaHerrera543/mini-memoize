# mini-memoize

A small memoisation decorator with a custom key function and a bounded, least-recently-used cache.

## Usage

```python
from mini_memoize import memoize

@memoize(maxsize=2)
def slow_add(a, b):
    print("computing")
    return a + b

slow_add(1, 2)  # prints "computing"
slow_add(1, 2)  # cached
slow_add(3, 4)  # prints "computing"
slow_add(1, 2)  # recomputes because 1,2 was evicted
```

A custom key function can be supplied. It receives the same arguments as the decorated function and must return a hashable value.

```python
@memoize(key_func=lambda a, b: (a, b), maxsize=10)
def multiply(a, b):
    return a * b
```

## Why this exists

Memoising a function is easy until you need to bound the memory it uses. An unbounded cache is a slow leak in a long-running process. This library keeps the implementation small and predictable: a single decorator, an optional custom key function, and an LRU eviction policy. The trade-off is that the cache is not thread-safe; wrap calls in your own lock if you need concurrency. That keeps the library free of hidden locks and makes the cost of synchronisation explicit.

## The awkward edge

The default key function sorts keyword arguments by name, so `f(a=1, b=2)` and `f(b=2, a=1)` hit the same cache entry. If your function distinguishes keyword order (which is unusual but possible with `**kwargs`), supply a custom key function. Also note that the key function must return a hashable value; passing an unhashable value raises `TypeError` from the underlying dictionary.
