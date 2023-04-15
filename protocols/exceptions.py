class InvalidEverythingCard(Exception):
    """
    Everything card can only be used at the end of a topic;
    it cannot be used with a tree message
    """


class DynamicMessageError(Exception):
    """
    A dynamic message was found where a static message was expected
    """
