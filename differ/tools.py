# coding: utf-8
from collections import namedtuple, Hashable


class Hashabledict(dict):
    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()


class Hashablelist(list):
    def __key(self):
        return tuple(k for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()


def make_hashable(thing):
    if isinstance(thing, Hashable):
        return thing
    elif isinstance(thing, list):
        ret = Hashablelist()
        for subthing in thing:
            ret.append(make_hashable(subthing))
        return ret
    elif isinstance(thing, dict):
        new_thing = Hashabledict()
        for k, v in thing.iteritems():
            new_thing[k] = make_hashable(v)
        return new_thing
    else:
        return thing

Match = namedtuple('Match', ['twin_index', 'ratio', 'val'])
