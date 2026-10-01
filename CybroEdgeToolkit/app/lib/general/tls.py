import ssl

from lib.general.paths import APP_DIR

CERTIFICATE_FILE = APP_DIR.joinpath("tls/private.crt").resolve()
KEY_FILE = APP_DIR.joinpath("tls/private.key").resolve()


def create_client_tls_context() -> ssl.SSLContext:
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

    # required in order for self-signed certificates to work
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    ssl_context.load_cert_chain(CERTIFICATE_FILE, KEY_FILE)

    return ssl_context


def create_server_tls_context() -> ssl.SSLContext:
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(CERTIFICATE_FILE, KEY_FILE)
    return ssl_context
