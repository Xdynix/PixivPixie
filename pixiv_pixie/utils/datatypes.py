import json


class Json:
    """General json object.
    >>> profile = Json({ \
        'name': 'John', \
        'tag': ['father', 'police'], \
        'address': {'country': 'US', 'state': 'CA'} \
    })
    >>> profile.name
    'John'
    >>> profile.name = 'Tom'
    >>> profile.name
    'Tom'
    >>> profile.tag[0]
    'father'
    >>> len(profile.tag)
    2
    >>> tag = profile.tag
    >>> tag
    ['father', 'police']
    >>> tag.append({'type': 'super_tag', 'value': 'superman'})
    >>> profile.tag[-1].value
    'superman'
    >>> profile.address.country
    'US'
    >>> profile.address.state = 'NY'
    >>> profile.address.state
    'NY'
    """

    __slots__ = ('_obj',)

    @classmethod
    def raw_data(cls, json_obj):
        if isinstance(json_obj, Json):
            return getattr(json_obj, '_obj')
        else:
            raise TypeError('Expect Json object.')

    @classmethod
    def from_string(cls, string):
        return cls(json.loads(string))

    @classmethod
    def from_bytes(cls, bytes_object, encoding='utf-8', **kwargs):
        return cls(json.loads(bytes_object.decode(encoding=encoding, **kwargs)))

    @classmethod
    def iter(cls, iterable):
        for item in iterable:
            if isinstance(item, (list, dict)):
                yield Json(item)
            else:
                yield item

    def __init__(self, obj):
        super().__setattr__('_obj', obj)

    def __repr__(self):
        return repr(self._obj)

    def __str__(self):
        return str(self._obj)

    def __eq__(self, other):
        if isinstance(other, Json):
            return self._obj == Json.raw_data(other)
        else:
            return self._obj == other

    def __getitem__(self, item):
        value = self._obj[item]
        if isinstance(value, (list, dict)):
            return Json(value)
        else:
            return value

    def __setitem__(self, key, value):
        self._obj[key] = value

    def __delitem__(self, key):
        del self._obj[key]

    def __len__(self):
        return len(self._obj)

    def __iter__(self):
        return Json.iter(self._obj)

    def __reversed__(self):
        return reversed(self._obj)

    def __contains__(self, item):
        return item in self._obj

    def __getattr__(self, item):
        if hasattr(self._obj, item):
            value = getattr(self._obj, item)
        else:
            value = self._obj[item]

        if isinstance(value, (list, dict)):
            return Json(value)
        else:
            return value

    def __setattr__(self, key, value):
        if hasattr(self._obj, key):
            setattr(self._obj, key, value)
        else:
            self._obj[key] = value

    def __delattr__(self, item):
        if hasattr(self._obj, item):
            delattr(self._obj, item)
        else:
            del self._obj[item]

    def __dir__(self):
        return dir(self._obj)


class LazyProperty:
    def __init__(self, func, property_name=None):
        if property_name is None:
            property_name = func.__name__

        self.func = func
        self.property_name = property_name

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.property_name, value)
            return value
