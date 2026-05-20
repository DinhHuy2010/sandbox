from json import dumps


class BaseObject:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<{}>".format(self.__class__.__name__)

    def export(self, format: str):
        raise NotImplementedError(
            "Export method not implemented for {}".format(self.__class__.__name__)
        )


class StringObject(BaseObject):
    def export(self, format):
        match format:
            case "json":
                return dumps(self.value)
            case "xml":
                return "<string>{}</string>".format(self.value)
            case "html":
                return "<p>{}</p>".format(self.value)
            case "python":
                return self.value
            case _:
                raise ValueError("Unsupported format: {}".format(format))


class ListObject(BaseObject):
    def __init__(self, value):
        elems = list(map(Object, value))
        super().__init__(elems)

    def export(self, format):
        match format:
            case "json":
                return dumps([elem.export("json") for elem in self.value])
            case "xml":
                return "<list>{}</list>".format(
                    "".join(
                        "<item>{}</item>".format(elem.export("xml"))
                        for elem in self.value
                    )
                )
            case "html":
                return "<ul>{}</ul>".format(
                    "".join(
                        "<li>{}</li>".format(elem.export("html")) for elem in self.value
                    )
                )
            case "python":
                return [elem.export("python") for elem in self.value]
            case _:
                raise ValueError("Unsupported format: {}".format(format))


class ForeignObject(BaseObject):
    def export(self, format):
        match format:
            case "python":
                return self.value
            case _:
                raise ValueError("Unsupported format: {}".format(format))


class Object:
    def __new__(cls, value):
        if isinstance(value, str):
            return StringObject(value)
        elif isinstance(value, list):
            return ListObject(value)
        return ForeignObject(value)


p = Object({})
l = Object(["a", "b", "c", object()])
print(l.export("json"))
