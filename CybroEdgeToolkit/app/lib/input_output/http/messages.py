from dataclasses import dataclass
from typing import Dict, Optional

LINE_END = "\r\n"
PROTOCOL_HTTP1_1 = "HTTP/1.1"


def split_headers(headers: str) -> Dict[str, str]:
    """Split HTTP headers string into a dictionary.
    """
    return dict(
        tuple(map(lambda v: v.strip(), x.split(":", 1)))
        for x in headers.split(LINE_END)
    )


def join_headers(headers: Dict[str, str]) -> str:
    """Combines header dictionary into HTTP header string.
    """
    return LINE_END.join(f"{k}: {v}" for k, v in headers.items())


@dataclass(frozen=True)
class HttpRequestMessage:
    """HTTP request message object representation.
    """
    method: str
    uri: str
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    protocol: str = PROTOCOL_HTTP1_1

    @classmethod
    def parse_request(cls, data: str):
        """Deserializes text HTTP request message to HttpRequestMessage
        object.
        """
        head, body = data.split(LINE_END + LINE_END)

        if head.find(LINE_END) != -1:
            request_line, headers = head.split(LINE_END, 1)
        else:
            request_line, headers = head, None

        method, uri, protocol = request_line.split(" ")

        return cls(
            method=method,
            uri=uri,
            headers=split_headers(headers) if headers is not None else None,
            body=body,
            protocol=protocol
        )

    def serialize(self) -> str:
        """Serializes request message object to text.
        """
        resp = f"{self.method} {self.uri} {self.protocol}"

        if self.headers is not None:
            headers = join_headers(self.headers)
            if len(headers) > 0:
                resp += f"{LINE_END}{headers}"

        resp += LINE_END + LINE_END

        if self.body is not None and self.body != "":
            resp += self.body

        return resp

    def __str__(self) -> str:
        return self.serialize()


@dataclass(frozen=True)
class HttpResponseMessage:
    """HTTP response message object representation.
    """
    status_code: int
    status_message: str
    headers: Optional[Dict[str, str]] = None
    body: str = ""
    protocol: str = PROTOCOL_HTTP1_1

    @classmethod
    def parse_response(cls, data: str):
        """Deserializes text HTTP response message to HttpResponseMessage
        object.
        """
        head, body = data.split(LINE_END + LINE_END)

        if head.find(LINE_END) != -1:
            status_line, headers = head.split(LINE_END, 1)
        else:
            status_line, headers = head, None

        protocol, code, message = status_line.split(" ", 2)

        return cls(
            status_code=int(code),
            status_message=message,
            headers=split_headers(headers) if headers is not None else None,
            body=body,
            protocol=protocol
        )

    @classmethod
    def ok(cls,
           headers: Optional[Dict[str, str]] = None,
           body: Optional[str] = None):
        """Create response for status OK.
        """
        return cls(
            status_code=200,
            status_message="OK",
            headers={} if headers is None else headers,
            body="" if body is None else body
        )

    @classmethod
    def bad_request(cls,
                    headers: Optional[Dict[str, str]] = None,
                    body: Optional[str] = None):
        """Create response for status 400.
        """
        return cls(
            status_code=400,
            status_message="Bad Request",
            headers={} if headers is None else headers,
            body="" if body is None else body
        )

    @classmethod
    def unauthorized(cls,
                     headers: Optional[Dict[str, str]] = None,
                     body: Optional[str] = None):
        """Create response for status 401.
        """
        return cls(
            status_code=401,
            status_message="Unauthorized",
            headers={} if headers is None else headers,
            body="Unauthorized access" if body is None else body
        )

    @classmethod
    def not_found(cls,
                  headers: Optional[Dict[str, str]] = None,
                  body: Optional[str] = None):
        """Create response for status 404.
        """
        return cls(
            status_code=404,
            status_message="Not found",
            headers={} if headers is None else headers,
            body="Page not found" if body is None else body
        )

    @classmethod
    def internal_server_error(cls,
                              headers: Optional[Dict[str, str]] = None,
                              body: Optional[str] = None):
        """Create response for status 500.
        """
        return cls(
            status_code=500,
            status_message="Internal Server Error",
            headers={} if headers is None else headers,
            body="" if body is None else body
        )

    def serialize(self) -> str:
        """Serializes response message object to text.
        """
        resp = f"{self.protocol} {self.status_code} {self.status_message}"

        if self.headers is not None:
            headers = join_headers(self.headers)
            if len(headers) > 0:
                resp += f"{LINE_END}{headers}"

        resp += LINE_END + LINE_END

        if self.body != "":
            resp += self.body

        return resp

    def __str__(self) -> str:
        return self.serialize()
