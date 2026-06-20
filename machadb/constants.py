"""
constants.py — The Sacred Numbers of MachaDB

These constants were discovered after 4 cups of filter coffee
and a heated argument about byte alignment at 2 AM.

Don't change these unless you want the database to go full ulta, macha.
"""

# ============================================================
# Page Configuration — the fundamental unit of I/O
# ============================================================
# 4096 bytes per page, same as SQLite, same as Linux page size.
# Why? Because our seniors said so and we're too scared to argue.
PAGE_SIZE = 4096

# How many pages to keep in memory before things get spicy
# 64 pages = 256 KB of buffer pool. Adjust maadthide.
DEFAULT_BUFFER_POOL_SIZE = 64

# ============================================================
# File Magic — so we don't accidentally open a random file
# ============================================================
MAGIC_BYTES = b'MCHA'  # MachaDB file signature, boss
FILE_VERSION = 1        # v1.0 — chai-powered edition

# ============================================================
# Type Codes — binary tags for serialized values
# ============================================================
TYPE_NULL = 0x00       # Nothing here macha
TYPE_INTEGER = 0x01    # sankhye — signed 64-bit integer
TYPE_FLOAT = 0x02      # dashaamsha — 64-bit double
TYPE_TEXT = 0x03        # pathya — UTF-8 string
TYPE_BOOLEAN = 0x04    # haan_illa — true/false

# ============================================================
# Page Header Layout
# ============================================================
# [2 bytes: row_count] [2 bytes: free_offset] [4 bytes: page_id]
PAGE_HEADER_SIZE = 8

# ============================================================
# Row Layout
# ============================================================
# Each row in a page:
# [1 byte: status] [2 bytes: data_length] [N bytes: data]
ROW_HEADER_SIZE = 3  # status + length prefix
ROW_STATUS_ACTIVE = 0x00
ROW_STATUS_DELETED = 0x01

# ============================================================
# File Header (Page 0 of every .tbl file)
# ============================================================
# [4 bytes: MAGIC] [1 byte: VERSION] [4 bytes: total_pages]
# [4 bytes: total_rows] [2 bytes: column_count]
# Rest is serialized schema
FILE_HEADER_FIXED_SIZE = 15

# ============================================================
# B-Tree Constants
# ============================================================
BTREE_NODE_HEADER_SIZE = 15  # type(1) + key_count(2) + parent(4) + next(4) + reserved(4)
BTREE_INTERNAL_NODE = 0x00
BTREE_LEAF_NODE = 0x01
BTREE_MAX_ORDER = 200  # max keys per node (calculated for int64 keys)

# ============================================================
# WAL Constants
# ============================================================
WAL_MAGIC = b'WLOG'
WAL_RECORD_BEGIN = 0x01
WAL_RECORD_INSERT = 0x02
WAL_RECORD_UPDATE = 0x03
WAL_RECORD_DELETE = 0x04
WAL_RECORD_COMMIT = 0x05
WAL_RECORD_ROLLBACK = 0x06
WAL_RECORD_CHECKPOINT = 0x07

# ============================================================
# Catalog
# ============================================================
CATALOG_FILENAME = "jamakhaana.json"

# ============================================================
# Mood Indicators (for status output)
# ============================================================
MOODS = [
    "surviving",
    "chill macha",
    "swalpa tension",
    "full scene",
    "nkn deployment today",
    "chai break needed",
    "auto-rickshaw mode",
    "filter coffee time",
]
