class AttrDict(dict):

    def __getattr__(self, key):
        if key.startswith('_'):
            raise AttributeError(key)
        val = self.get(key)
        if isinstance(val, dict) and not isinstance(val, AttrDict):
            val = AttrDict(val)
            self[key] = val
        return val

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            if isinstance(value, dict) and not isinstance(value, AttrDict):
                value = AttrDict(value)
            self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]

    def __bool__(self):
        return len(self) > 0

    def copy(self):
        return AttrDict({k: v.copy() if isinstance(v, AttrDict) else v for k, v in self.items()})

    @staticmethod
    def from_nested(data):
        if isinstance(data, dict):
            return AttrDict({k: AttrDict.from_nested(v) for k, v in data.items()})
        elif isinstance(data, list):
            return [AttrDict.from_nested(v) for v in data]
        return data
