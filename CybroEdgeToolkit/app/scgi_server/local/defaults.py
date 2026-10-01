# how often will system clear plc info table [minutes]
PLC_INFO_CLEAR_PERIOD = 10
# how long an unused entry exists in the plc info table, before it may be
# removed [minutes]
PLC_INFO_LIFETIME = 10
# abus maximum message size [bytes]
MAX_FRAME_BYTES = 1000
# address that the push service will use to communicate with controllers
PUSH_NAD = 1001
# address that the read/write service will use to communicate with controllers
RW_NAD = 1002
# address that the autodetect will use to communicate with controllers
AUTODETECT_NAD = 1003

ABUS_BROADCAST_PORT = 8442
