# Differ
### Yet another object comparison tool.
This module provides a way to find differences between simple and complex (nested) objects.

This module do what others do (think of [difflib](https://docs.python.org/3/library/difflib.html) / [DeepDiff](http://deepdiff.readthedocs.io/en/latest/) / [ObjDiff](http://pythonhosted.org/objdiff/)), but the way I like, and with some magic.

### Usage:
```python
from differ import Differ
differ = Differ()
diff = differ.compare(object1, object2)
# diff is a Difference instance that can be traversed:
```

You can also play with inheritance from the Diffing class, that will override the bitwise xor operator ('^') so it will produces differencies:
```python
from differ import Diffing
class MyClass(Diffing):
    pass

a = MyClass()
b = MyClass()
diff = a ^ b  # diff is a Difference instance
```
