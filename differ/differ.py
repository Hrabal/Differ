# coding: utf-8
from copy import copy
from itertools import product
from datetime import datetime
from difflib import SequenceMatcher
from collections import OrderedDict

from tools import make_hashable, Match


class Difference(object):
    pass


class Differ(object):

    def __init__(self, excluded_keys=None, ignore_new=False, try_cast=False, exclude_cast=False):
        self.excluded_keys = set(excluded_keys) if excluded_keys else set()
        self.ignore_added = ignore_new
        self.try_cast = try_cast
        self.exclude_cast = exclude_cast or []
        self.report = {}

    def _get_compare_method(self, obj):
        compare_methods = OrderedDict([
            (lambda x: isinstance(x, dict), self._dict_compare),
            (lambda x: hasattr(x, '__iter__'), self._iter_compare),
            (lambda x: hasattr(x, '__eq__'), self._leaf_compare),
            (lambda x: isinstance(x, object), self._obj_compare)
        ])
        return next((value for condition, value in compare_methods.items() if condition(obj)), '')

    def _format_report(self, a, r, m, s):
        return {k: v for k, v in {'added': a, 'removed': r, 'modified': m, 'same': s}.items() if v}

    def _prepare_object(self, obj, new_keys=None, key=None):
        new_k = set(new_keys) if new_keys else set()
        if isinstance(obj, dict):
            return {k: self._prepare_object(v, new_keys=new_keys, key=k) for k, v in obj.iteritems()
                    if k not in self.excluded_keys | new_k}
        elif hasattr(obj, '__iter__'):
            return [self._prepare_object(o, new_keys=new_keys, key=key) for o in obj]
        else:
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

    def _obj_compare(self, v1, v2, key=None):
        return self._dict_compare(v1.__dict__, v2.__dict__, key=key)

    def _leaf_compare(self, v1, v2, key=None):
        added = {v2} if not v1 and v2 else set()
        removed = {v1} if v1 and not v2 else set()
        modified = {'origin': v1, 'new': v2} if v1 != v2 else {}
        same = v1 if v1 == v2 else set()
        return added, removed, modified, same, set()

    def _iter_compare(self, l1, l2, key=None):
        checked = same = set()
        l1_filtered, l2_filtered = map(lambda x: self._prepare_object(x, key=key), (l1, l2))
        ar = len(l1_filtered) - len(l2_filtered)
        added, removed = set(), set()
        modified = {}
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
                same.add(make_hashable(el1))
            elif match.ratio == 0.0 and ar:
                [added, removed][ar > 0].add([str(el2), str(el1)][ar > 0])
            else:
                if el1 != el2:
                    a, r, m, s, c = self._get_compare_method(el1)(el1, el2)
                    checked |= c
                    if any((a, r, m)):
                        modified[i] = self._format_report(a, r, m, None)
        return added, removed, modified, same, checked

    def _dict_compare(self, d1, d2, key=None):
        same = set()
        d1_filtered, d2_filtered = map(lambda x: self._prepare_object(x, key=key), (d1, d2))
        keys1, keys2 = map(lambda d: set(d.keys()) - self.excluded_keys, (d1_filtered, d2_filtered))
        intersect_keys = keys1.intersection(keys2)
        removed = keys1 - keys2
        added = keys2 - keys1
        checked = copy(intersect_keys)
        if self.ignore_added:
            added = set()
            intersect_keys -= added
        modified = {}
        for k in intersect_keys:
            v1, v2 = d1_filtered[k], d2_filtered[k]
            if v1 != v2:
                compare_method = self._get_compare_method(v1)
                a, r, m, s, c = compare_method(v1, v2, k)
                checked |= c
                if any((a, r, m)):
                    modified[k] = self._format_report(a, r, m, None)
            else:
                same.add(k)
        return added, removed, modified, same, checked

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
