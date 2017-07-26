# coding: utf-8
from itertools import product
from datetime import datetime
from difflib import SequenceMatcher
from collections import OrderedDict
from types import ComplexType, FloatType, LongType, IntType, UnicodeType
DirectComparableTypes = (IntType, LongType, FloatType, ComplexType, UnicodeType)

from tools import make_hashable, Match


class Difference(object):
    def __init__(self, original, new, key=None, **kwargs):
        self.original = original
        self.new = new
        self.key = key
        self.added = self.same = self.removed = set()
        self.modified = dict()
        self.__dict__.update(kwargs)

    def __str__(self):
        return str(self.__dict__)

    def __bool__(self):
        return any((self.added, self.modified, self.removed))


class Differ(object):

    def __init__(self, excluded_keys=None, ignore_new=False, try_cast=False, exclude_cast=False):
        self.excluded_keys = set(excluded_keys) if excluded_keys else set()
        self.ignore_added = ignore_new
        self.try_cast = try_cast
        self.exclude_cast = exclude_cast or []

    def diff_finder(func):
        def wrap(self, *args, **kwargs):
            if args[0].pop('debug', None):
                pass
            return func(self, *args, **kwargs)
        return wrap

    def _get_compare_method(self, obj):
        compare_methods = OrderedDict([
            (lambda x: isinstance(x, dict), self._dict_compare),
            (lambda x: hasattr(x, '__iter__'), self._iter_compare),
            (lambda x: hasattr(x, '__eq__'), self._leaf_compare),
            (lambda x: isinstance(x, object), self._obj_compare)
        ])
        return next((value for condition, value in compare_methods.items() if condition(obj)), '')

    def _prepare_object(self, obj, new_keys=None, key=None):
        new_k = set(new_keys) if new_keys else set()
        if isinstance(obj, dict):
            return {k: self._prepare_object(v, new_keys=new_keys, key=k) for k, v in obj.iteritems()
                    if k not in self.excluded_keys | new_k}
        elif hasattr(obj, '__iter__'):
            return [self._prepare_object(o, new_keys=new_keys, key=key) for o in obj]
        elif hasattr(obj, '__eq__'):
            if self.try_cast and (not key or key not in self.exclude_cast):
                try:
                    if not obj.startswith('0'):
                        return float(obj)
                except ValueError:
                    pass
                try:
                    return datetime.strptime(obj, '%Y%m%d')
                except ValueError:
                    pass
                try:
                    return datetime.strptime(obj, '%Y%m%d %H:%M%S')
                except ValueError:
                    pass
            return obj
        elif hasattr(obj, '__dict__'):
            return self._prepare_object(obj.__dict__)
        else:
            return obj

    @diff_finder
    def _obj_compare(self, o1, o2, key=None):
        o1, o1 = map(lambda x: self._prepare_object(x, key=key), (o2.__dict__, o2.__dict__))
        return self._dict_compare(o1, o1, key=key)

    @diff_finder
    def _leaf_compare(self, v1, v2, key=None):
        return Difference(v1, v2, key=key, **{'added': {v2} if not v1 and v2 else set(),
                                              'removed': {v1} if v1 and not v2 else set(),
                                              'modified': {'origin': v1, 'new': v2} if v1 != v2 else {},
                                              'same': v1 if v1 == v2 else set()
                                              })

    @diff_finder
    def _iter_compare(self, l1, l2, key=None):
        diff = Difference(l1, l2, key=key)
        l1_filtered, l2_filtered = map(lambda x: self._prepare_object(x, key=key), (l1, l2))
        ar = len(l1_filtered) - len(l2_filtered)
        matches = {}
        for ((i1, obj1), (i2, obj2)) in product(enumerate(l1_filtered), enumerate(l2_filtered)):
            if type(obj1) == type(obj2):
                if isinstance(obj1, dict):
                    r = len(self._dict_compare(obj1, obj2)[3]) / len(obj1.keys())
                elif hasattr(obj1, '__iter__'):
                    r = len(self._iter_compare(obj1, obj2)[3]) / len(obj1)
                else:
                    obj1, obj2 = map(str, (obj1, obj2))
                    r = SequenceMatcher(None, obj1, obj2).ratio()
            else:
                r = 0.0
            matches.setdefault(i1, []).append(Match(i2, r, obj2))

        for i, el1 in enumerate(l1_filtered):
            match = sorted(matches.get(i, []), key=lambda m: m.ratio, reverse=True)[0]
            el2 = l2_filtered[match.twin_index]
            if match.ratio == 1.0:
                diff.same.add(make_hashable(el1))
            elif match.ratio == 0.0 and ar:
                group, element = ((diff.added, str(el2)), (diff.removed, str(el1)))[ar > 0]
                group.add(element)
            else:
                if el1 != el2:
                    diff.modified[i] = self._get_compare_method(el1)(el1, el2)
        return diff

    @diff_finder
    def _dict_compare(self, d1, d2, key=None):
        diff = Difference(d1, d2, key=key)
        d1_filtered, d2_filtered = map(lambda x: self._prepare_object(x, key=key), (d1, d2))
        keys1, keys2 = map(lambda d: set(d.keys()) - self.excluded_keys, (d1_filtered, d2_filtered))
        intersect_keys = keys1.intersection(keys2)
        if self.ignore_added:
            added = set()
            intersect_keys -= added
        for k in intersect_keys:
            v1, v2 = d1_filtered[k], d2_filtered[k]
            if v1 != v2:
                diff.modified[k] = self._get_compare_method(v1)(v1, v2, k)
            else:
                diff.same.add(k)
        return diff

    @diff_finder
    def compare(self, obj1, obj2):
        method1, method2 = map(self._get_compare_method, (obj1, obj2))
        if method1 != method2:
            raise ValueError
        return method1(obj1, obj2)


class Diffing(object):

    compare = lambda x, y: Differ().compare(x, y)

    def __rxor__(self, other):
        return Diffing.compare(other, self)

    def __xor__(self, other):
        return Diffing.compare(self, other)

    def __call__(self, value1, value2):
        return Diffing.compare(value1, value2)
