SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUD = "9600"
VALUE_SEPARATOR = '\\t'
PAYLOAD_SEPARATOR = '\\n\\r'
END_OF_PAYLOAD = "\r"
SERIAL_COLLECT_INTERVAL = 0.1
NB_OF_TELEMETRY_VALUES = 35
TELEMETRY_TABLE_NAME = 'TELEMETRY'
TELEMETRY_LOG_TABLE_NAME = 'TELEMETRY_LOG'
TELEMETRY_TYPE_TABLE_NAME = 'TELEMETRY_TYPE'
PREDICTION_TABLE_NAME = 'PREDICTION'
ANALYTE_TABLE_NAME = 'ANALYTE'
EVENT_TABLE_NAME = 'EVENT'
TELEMETRY_DATABASE_PATH = '/home/pi/telemetryEdgeDatabase.db'
TELEMETRY_DATABASE_NAME = f'sqlite:///{TELEMETRY_DATABASE_PATH}'
MI_DATABASE_PATH = '/home/pi/miEdgeDatabase.db'
MI_DATABASE_NAME = f'sqlite:///{MI_DATABASE_PATH}'
TELEMETRY_TYPE_AND_UNIT = [
    {"type": "RRF0", "unit": "OHM"},
    {"type": "CHR0", "unit": "OHM"},
    {"type": "CHR1", "unit": "OHM"},
    {"type": "CHR2", "unit": "OHM"},
    {"type": "CHR3", "unit": "OHM"},
    {"type": "CHR4", "unit": "OHM"},
    {"type": "CHR5", "unit": "OHM"},
    {"type": "CHR6", "unit": "OHM"},
    {"type": "CHR7", "unit": "OHM"},
    {"type": "CHR8", "unit": "OHM"},
    {"type": "CHR9", "unit": "OHM"},
    {"type": "CHR10", "unit": "OHM"},
    {"type": "CHR11", "unit": "OHM"},
    {"type": "CHR12", "unit": "OHM"},
    {"type": "CHR13", "unit": "OHM"},
    {"type": "CHR14", "unit": "OHM"},
    {"type": "CHR15", "unit": "OHM"},
    {"type": "CHR16", "unit": "OHM"},
    {"type": "CHR17", "unit": "OHM"},
    {"type": "CHR18", "unit": "OHM"},
    {"type": "CHR19", "unit": "OHM"},
    {"type": "CHR20", "unit": "OHM"},
    {"type": "CHR21", "unit": "OHM"},
    {"type": "CHR22", "unit": "OHM"},
    {"type": "CHR23", "unit": "OHM"},
    {"type": "CHR24", "unit": "OHM"},
    {"type": "CHR25", "unit": "OHM"},
    {"type": "CHR26", "unit": "OHM"},
    {"type": "CHR27", "unit": "OHM"},
    {"type": "CHR28", "unit": "OHM"},
    {"type": "CHR29", "unit": "OHM"},
    {"type": "CHR30", "unit": "OHM"},
    {"type": "CHR31", "unit": "OHM"},
    {"type": "T0", "unit": "C"},
    {"type": "H0", "unit": "PRCRH"}
]
BFU_DEVICE_ID_INDEX = 36
CREATED_AT_INDEX = 37
NB_OF_THINGSBOARD_CONNECT_ATTEMPTS = 10
