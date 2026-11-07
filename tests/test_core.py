import unittest

from mini_memoize import memoize, MemoizedFunction


class TestMemoize(unittest.TestCase):
    def test_default_key_uses_args_and_kwargs(self):
        calls = []

        @memoize()
        def add(a, b):
            calls.append((a, b))
            return a + b

        self.assertEqual(add(1, 2), 3)
        self.assertEqual(add(1, 2), 3)
        self.assertEqual(add(2, 1), 3)
        self.assertEqual(len(calls), 2)

    def test_keyword_order_does_not_matter(self):
        calls = []

        @memoize()
        def f(a, b):
            calls.append((a, b))
            return a * b

        self.assertEqual(f(a=2, b=3), 6)
        self.assertEqual(f(b=3, a=2), 6)
        self.assertEqual(len(calls), 1)

    def test_custom_key_function(self):
        calls = []

        def key(a, b):
            return (a, b)

        @memoize(key_func=key)
        def f(a, b):
            calls.append((a, b))
            return a - b

        self.assertEqual(f(5, 3), 2)
        self.assertEqual(f(5, 3), 2)
        self.assertEqual(f(3, 5), -2)
        self.assertEqual(len(calls), 2)

    def test_key_function_receives_all_arguments(self):
        seen = []

        def key(*args, **kwargs):
            seen.append((args, kwargs))
            return (args, tuple(sorted(kwargs.items())))

        @memoize(key_func=key)
        def f(a, b=0):
            return a + b

        f(1, b=2)
        self.assertEqual(seen, [((1,), {"b": 2})])

    def test_maxsize_evicts_least_recently_used(self):
        calls = []

        @memoize(maxsize=2)
        def f(x):
            calls.append(x)
            return x * 10

        self.assertEqual(f(1), 10)
        self.assertEqual(f(2), 20)
        # Access 1 to make it recently used.
        self.assertEqual(f(1), 10)
        # Insert 3, which should evict 2.
        self.assertEqual(f(3), 30)
        # 2 is gone, so this call recomputes.
        self.assertEqual(f(2), 20)
        self.assertEqual(calls, [1, 2, 3, 2])

    def test_maxsize_one(self):
        calls = []

        @memoize(maxsize=1)
        def f(x):
            calls.append(x)
            return x

        self.assertEqual(f(1), 1)
        self.assertEqual(f(1), 1)
        self.assertEqual(f(2), 2)
        self.assertEqual(f(1), 1)
        self.assertEqual(calls, [1, 2, 1])

    def test_maxsize_none_is_unbounded(self):
        calls = []

        @memoize(maxsize=None)
        def f(x):
            calls.append(x)
            return x

        for i in range(100):
            f(i)
        for i in range(100):
            f(i)
        self.assertEqual(len(calls), 100)

    def test_maxsize_must_be_positive_or_none(self):
        with self.assertRaises(ValueError):
            @memoize(maxsize=0)
            def f():
                pass

        with self.assertRaises(ValueError):
            @memoize(maxsize=-1)
            def f():
                pass

    def test_cache_clear_resets_state(self):
        calls = []

        @memoize()
        def f(x):
            calls.append(x)
            return x

        f(1)
        f(1)
        self.assertEqual(f.cache_info(), (1, 1, 0, 1, 128))
        f.cache_clear()
        self.assertEqual(f.cache_info(), (0, 0, 0, 0, 128))
        f(1)
        self.assertEqual(calls, [1, 1])

    def test_cache_info_tracks_evictions(self):
        @memoize(maxsize=1)
        def f(x):
            return x

        f(1)
        f(2)
        self.assertEqual(f.cache_info(), (0, 2, 1, 1, 1))

    def test_wrapped_attribute(self):
        def original(x):
            return x

        wrapped = memoize()(original)
        self.assertIs(wrapped.__wrapped__, original)

    def test_key_function_exception_propagates(self):
        def bad_key(x):
            raise RuntimeError("bad key")

        @memoize(key_func=bad_key)
        def f(x):
            return x

        with self.assertRaises(RuntimeError):
            f(1)

    def test_unhashable_key_raises_type_error(self):
        @memoize(key_func=lambda x: x)
        def f(x):
            return x

        with self.assertRaises(TypeError):
            f([1, 2])

    def test_decorator_returns_memoized_function_instance(self):
        @memoize()
        def f():
            return 1

        self.assertIsInstance(f, MemoizedFunction)

    def test_memoized_function_requires_callables(self):
        with self.assertRaises(TypeError):
            MemoizedFunction(1, lambda: None)
        with self.assertRaises(TypeError):
            MemoizedFunction(lambda: None, 1)


if __name__ == "__main__":
    unittest.main()
