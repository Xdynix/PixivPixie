import json


class JsonMixin:
    """Some json related method.
    >>> JsonDict.from_bytes(b'{"name": "Nobody"}').name
    'Nobody'
    >>> len(JsonArray.from_string('[1, 2, 3]'))
    3
    """

    @classmethod
    def from_string(cls, string):
        return cls(json.loads(string))

    @classmethod
    def from_bytes(cls, bytes_object, encoding='utf-8', **kwargs):
        return cls(json.loads(bytes_object.decode(encoding=encoding, **kwargs)))


class JsonDict(dict, JsonMixin):
    """General json object that attributes to be bound to and also behaves like
    a dict.
    This is inspired by https://github.com/upbit/pixivpy.
    >>> profile = JsonDict({ \
        'name': 'John', \
        'tag': ['father', 'police'], \
        'address': {'country': 'US', 'state': 'CA'} \
    })
    >>> profile.name
    'John'
    >>> profile.name = 'Tom'
    >>> profile.name
    'Tom'
    >>> profile.tag.append({'type': 'super_tag', 'value': 'superman'})
    >>> profile.tag[-1].value
    'superman'
    >>> profile.address.country
    'US'
    >>> profile.address.state = 'NY'
    >>> profile.address.state
    'NY'
    """

    def __getitem__(self, key):
        item = super(JsonDict, self).__getitem__(key)
        if isinstance(item, list) and not isinstance(item, JsonArray):
            self[key] = JsonArray(item)
        elif isinstance(item, dict) and not isinstance(item, JsonDict):
            self[key] = JsonDict(item)
        else:
            return item
        return super(JsonDict, self).__getitem__(key)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(
                r"'JsonDict' object has no attribute '%s'" % key
            )

    def __setattr__(self, key, value):
        try:
            return super(JsonDict, self).__setitem__(key, value)
        except KeyError:
            raise AttributeError(
                r"'JsonDict' object has no attribute '%s'" % key
            )


class JsonArray(list, JsonMixin):
    """General json array proxy for JsonDict.
    """

    def __getitem__(self, key):
        item = super(JsonArray, self).__getitem__(key)
        if isinstance(item, list) and not isinstance(item, JsonArray):
            self[key] = JsonArray(item)
        elif isinstance(item, dict) and not isinstance(item, JsonDict):
            self[key] = JsonDict(item)
        else:
            return item
        return super(JsonArray, self).__getitem__(key)
