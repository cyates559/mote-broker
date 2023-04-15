from json import JSONEncoder, dumps as json_encode


class OutgoingMessageJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return o.decode()
        return super().default(o)


def stringify(tree_item) -> bytes:
    s = json_encode(tree_item, cls=OutgoingMessageJSONEncoder)
    return s.encode()
