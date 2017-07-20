# Differ
### Jet another object comparison tool.
This module provides a way to find differences between simple and complex (nested) objects.

This module do what others do (think of [difflib](https://docs.python.org/3/library/difflib.html) / [DeepDiff](http://deepdiff.readthedocs.io/en/latest/) / [ObjDiff](http://pythonhosted.org/objdiff/)), but the way I like, and with some magic.

### Usage:
```python
from differ import Differ
differ = Differ()
added, removed, modified, same, checked = differ.compare(object1, object2)

# Or access the results later in the code:
differ.compare(object1, object2)
...
print(differ.added, differ.removed)
```

You can also play with inheritance from the Diffing class, that will provide you the brand new keyword '?':
```python
from differ import Diffing
class MyClass(Diffing):
    pass

a = MyClass()
b = MyClass()
diff = a ? b  # diff is a Differ instance
```

You can also use the magic, and make everything differable:
```python
from differ import differencies
# now, some python objects respond to the '?' keyword ''''''natively''''''

a = b = {}
diff = a ? b
```
