import copy
import itertools
from difflib import SequenceMatcher
from collections import OrderedDict, namedtuple

DIFF_TYPES = ('ADD', 'REM', 'MOD')

Match = namedtuple('Match', ['twin_index', 'ratio', 'val'])

class Difference(object):

    def __init__(self, typ, key, new=None, old=None, val=None):
        if typ not in DIFF_TYPES:
            raise Exception('This diff is too different!')
        self.typ = typ
        self.key = key
        if self.typ = 'ADD':
            self.val = new
        if self.typ = 'REM':
            self.val = old
        if self.typ = 'MOD':
            self.val = val

class Differ(object):

    def __init__(self, excluded_keys=None, ignore_new=False):
        self.excluded_keys = set(excluded_keys) if excluded_keys else set()
        self.ignore_added = ignore_new
        self.report = {}

    def _get_compare_method(self, obj):
        compare_methods = OrderedDict([
                (lambda x: isinstance(x, dict), self._dict_compare),
                (lambda x: hasattr(x, '__iter__'), self._iter_compare),
                (lambda x: True, self._leaf_compare)
            ])
        return next((value for condition, value in compare_methods.items() if condition(obj)), '')

    def _format_report(self, a, r, m, s):
        return {k: v for k, v in {'added': a, 'removed': r, 'modified': m, 'same': s}.items() if v}

    def _prepare_object(self, obj, new_keys=None):
        new_k = set(new_keys) if new_keys else set()
        if isinstance(obj, dict):
            return {k: self._prepare_object(v) for k, v in obj.iteritems() if k not in self.excluded_keys | new_k}
        elif hasattr(obj, '__iter__'):
            return [self._prepare_object(o) for o in obj]
        else:
            return obj

    def _leaf_compare(self, v1, v2):
        added = set([v2, ]) if not v1 and v2 else set()
        removed = set([v1, ]) if v1 and not v2 else set()
        modified = {'origin': v1, 'test': v2} if v1 != v2 else {}
        same = v1 if v1 == v2 else set()
        return added, removed, modified, same, set()

    def _iter_compare(self, l1, l2):
        checked = set()
        same = set()
        l1_filtered, l2_filtered = map(self._prepare_object, (l1, l2))
        ar = len(l1_filtered) - len(l2_filtered)
        added, removed = set(), set()
        modified = {}
        matches = {}
        for ((i1, obj1), (i2, obj2)) in itertools.product(enumerate(l1_filtered), enumerate(l2_filtered)):
            if type(obj1) == type(obj2):
                if isinstance(obj1, dict):
                    r = 100 * len(self._dict_compare(obj1, obj2)[3]) / len(obj1.keys()) / 100
                elif hasattr(obj1, '__iter__'):
                    r = 100 * len(self._dict_compare(obj1, obj2)[3]) / len(obj1) / 100
                else:
                    obj1, obj2 = map(str, (obj1, obj2))
                    r = SequenceMatcher(None, obj1, obj2).ratio()
            else:
                r = 0.0
            m = Match(i2, r, obj2)
            matches.setdefault(i1,[]).append(m)
        print matches
        for i, el1 in enumerate(l1_filtered):
            match = sorted(matches.get(i, []), key=lambda m: m.ratio, reverse=True)[0]
            el2 = l2_filtered[match.twin_index]
            if match.ratio == 1.0:
                same.add(el1)
            elif match.ratio == 0.0 and ar:
                [added, removed][ar > 0].add([str(el2), str(el1)][ar > 0])
            else:
                if el1 != el2:
                    a, r, m, s, c = self._get_compare_method(el1)(el1, el2)
                    checked |= c
                    if any((a, r, m)):
                        modified[i] = self._format_report(a, r, m, None)
        return added, removed, modified, same, checked

    def _dict_compare(self, d1, d2):
        d1_filtered, d2_filtered = map(self._prepare_object, (d1, d2))
        keys1, keys2 = map(lambda d: set(d.keys()) - self.excluded_keys, (d1_filtered, d2_filtered))
        intersect_keys = keys1.intersection(keys2)
        removed = keys1 - keys2
        added = keys2 - keys1
        checked = copy.copy(intersect_keys)
        if self.ignore_added:
            added = set()
            intersect_keys -= added
        modified = {}
        for k in intersect_keys:
            v1, v2 = d1_filtered[k], d2_filtered[k]
            if v1 != v2:
                a, r, m, s, c = self._get_compare_method(v1)(v1, v2)
                checked |= c
                if any((a, r, m)):
                    modified[k] = self._format_report(a, r, m, None)
        same = set(o for o in intersect_keys if d1_filtered[o] == d2_filtered[o])
        return added, removed, modified, same, checked

    def compare(self, obj1, obj2):
        return self._get_compare_method(obj1)(obj1, obj2)
