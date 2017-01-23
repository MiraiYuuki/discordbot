import sqlite3
import traceback

class LogDB(object):
    def __init__(self, path):
        connection = sqlite3.connect(path)
        connection.executescript("""CREATE TABLE IF NOT EXISTS
            error_v1 (
                _server_id TEXT,
                _user_id TEXT,
                _invocation TEXT,
                _classname TEXT,
                _description TEXT,
                _trace TEXT
            );
            CREATE TABLE IF NOT EXISTS
            invalid_command_v1 (
                _server_id TEXT,
                _user_id TEXT,
                _invocation TEXT
            )
        """)
        connection.commit()

        self.connection = connection

    def log_current_error(self, original_msg, exception):
        server_id = original_msg.server.id if original_msg.server else ":DM"

        self.connection.execute("INSERT INTO error_v1 VALUES (?, ?, ?, ?, ?, ?)",
            (server_id, "{0}:{1}".format(original_msg.author.name, original_msg.author.id),
             original_msg.content, exception.__class__.__name__, str(exception),
             traceback.format_exc()))
        self.connection.commit()

    def log_invalid_command(self, original_msg):
        server_id = original_msg.server.id if original_msg.server else ":DM"

        self.connection.execute("INSERT INTO invalid_command_v1 VALUES (?, ?, ?, ?, ?, ?)",
            (server_id, "{0}:{1}".format(original_msg.author.name, original_msg.author.id),
             original_msg.content))
        self.connection.commit()
