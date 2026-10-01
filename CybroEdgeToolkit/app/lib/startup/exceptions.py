class TCPPortError(Exception):
    pass


class UDPPortError(Exception):
    pass


class MissingError(Exception):
    def __init__(self):
        super().__init__("Missing exception")
