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
