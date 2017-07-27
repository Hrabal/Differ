# coding: utf-8
from datetime import datetime
from difflib import SequenceMatcher
from collections import OrderedDict
from itertools import product, chain, izip_longest
import __builtin__
builtin_types = [t for t in __builtin__.__dict__.itervalues() if isinstance(t, type)]

from tools import make_hashable, Match

REMOVAL = 'REMOVAL'
MODIFICATION = 'MODIFICATION'
ADDITION = 'ADDITION'

class Difference(object):
    def __init__(self, original, new, key=None, **kwargs):
        self.original_val = original
        self.new_val = new
        self.key = key
        self._added = self._same = self._removed = set()
        self._modified = dict()
        mods = kwargs.pop('modified', None)
        if mods:
            map(lambda k, v: self.add_difference(k, v), mods.items())
        self.__dict__.update(kwargs)

    def __str__(self):
        return str({k: v for k, v in self.__dict__.iteritems() if v and k not in ('key', )})

    def __repr__(self):
        return str(self)

    def __bool__(self):
        return any((self._added, self._modified, self._removed))

    def add_difference(self, k, diff):
        self._modified[k] = diff

    def __iter__(self):
        iter_couples = zip((MODIFICATION, ADDITION, REMOVAL), (self._modified.iteritems(), enumerate(self._added), enumerate(self._removed)))
        iterators = map(lambda (typ, itrtr): izip_longest(tuple(), itrtr, fillvalue=typ), iter_couples)
        for typ, iterator in chain(iterators):
            for key, difference in iterator():
                print typ, key, difference
                if difference:
                    yield typ, (key, difference)

    @property
    def same(self):
        return iter(self._same)

    @property
    def added(self):
        return iter(self._added)

    @property
    def removed(self):
        return iter(self._removed)

    @property
    def modified(self):
        return self._modified.iteritems()


class Differ(object):

    def __init__(self, excluded_keys=None, ignore_new=False, try_cast=False, exclude_cast=False):
        self.excluded_keys = set(excluded_keys) if excluded_keys else set()
        self.ignore_added = ignore_new
        self.try_cast = try_cast
        self.exclude_cast = exclude_cast or []

    def _get_compare_method(self, obj):
        def is_comparable(obj):
            try:
                type(obj)() == type(obj)()
                return True
            except (ValueError, TypeError):
                return False

        compare_methods = OrderedDict([
            (lambda x: isinstance(x, dict), self._dict_compare),
            (lambda x: hasattr(x, '__iter__'), self._iter_compare),
            (lambda x: type(x) in builtin_types and is_comparable(x), self._leaf_compare),
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

    def _obj_compare(self, o1, o2, key=None):
        o1, o1 = map(lambda x: self._prepare_object(x, key=key), (o2.__dict__, o2.__dict__))
        return self._dict_compare(o1, o1, key=key)

    def _leaf_compare(self, v1, v2, key=None):
        return Difference(v1, v2, key=key, **{'_added': {v2} if not v1 and v2 else set(),
                                              '_removed': {v1} if v1 and not v2 else set(),
                                              '_same': v1 if v1 == v2 else set()
                                              })

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
                diff._same.add(make_hashable(el1))
            elif match.ratio == 0.0 and ar:
                group, element = ((diff._added, str(el2)), (diff._removed, str(el1)))[ar > 0]
                group.add(element)
            else:
                if el1 != el2:
                    diff._modified[i] = self._get_compare_method(el1)(el1, el2)
        return diff

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
                diff._modified[k] = self._get_compare_method(v1)(v1, v2, k)
            else:
                diff._same.add(k)
        return diff

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
