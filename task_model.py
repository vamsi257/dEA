import sqlite3
import pickle


def save_task_to_database(date, time, filenames, filetype):
    # Connect to SQLite database
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    serialized_filenames = pickle.dumps(filenames)

    # Create tasks table if it doesn't exist
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            filenames BLOB,
            filetype TEXT,
            result TEXT,
            status TEXT
        )
    """
    )

    # Save task to database
    cursor.execute(
        """
        INSERT INTO tasks (date,time,filenames,filetype, status)
        VALUES (?,?,?,?, 'pending')
    """,
        (date, time, serialized_filenames, filetype),
    )

    conn.commit()
    cursor.close()
    # conn.close()

    task_id = cursor.lastrowid
    return task_id