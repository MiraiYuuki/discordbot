import sqlite3
import os
import json

path = os.getenv("BOT_CONFIG_PATH", "configuration.db")
print("config: connecting")
_connection = sqlite3.connect(path)
_connection.execute("""CREATE TABLE IF NOT EXISTS
    configuration (
        _key TEXT,
        _value TEXT
    )
""")
_connection.commit()
_cache = {}

def get_json(key):
    return (_connection.execute("SELECT _value FROM configuration WHERE _key = ?", (key,)).fetchone() or (None,)) [0]

def get(key, default=None):
    if key in _cache:
        return _cache[key]
    
    jsval = get_json(key)

    if jsval is None:
        return default

    pyval = json.loads(jsval)
    _cache[key] = pyval
    return pyval

def write(key, value):
    write_direct(key, json.dumps(value))

def write_direct(key, value):
    k = _connection.execute("UPDATE configuration SET _value = ? WHERE _key = ?", (value, key))
    if k.rowcount == 0:
        _connection.execute("INSERT INTO configuration VALUES (?, ?)", (key, value))
    _connection.commit()
    
    try:
        del _cache[key]
    except KeyError:
        pass

def flush():
    global _cache
    _cache = {}

