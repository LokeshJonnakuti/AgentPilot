import sqlite3
import threading
from contextlib import ExitStack

from openagent.agent.config import config

db_path = config['system']['db-path']
sql_thread_lock = threading.Lock()


def execute(query, params=None):  # , is_async=False):
    # exit_stack = ExitStack()
    # if is_async:
    #     exit_stack.enter_context(sql_thread_lock)
    with sql_thread_lock:
        # Connect to the database
        conn = sqlite3.connect(db_path)

        # Create a cursor object
        cursor = conn.cursor()

        # Execute the query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Commit the changes
        conn.commit()

        # Close the cursor and connection
        cursor.close()
        conn.close()
        return cursor.lastrowid


def get_results(query, params=None, return_type='rows'):
    # Connect to the database
    conn = sqlite3.connect(db_path)

    # Create a cursor object
    cursor = conn.cursor()

    # Execute the query
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    # Fetch all the rows as a list of tuples
    rows = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Return the rows
    if return_type == 'list':
        return [row[0] for row in rows]
    elif return_type == 'dict':
        return {row[0]: row[1] for row in rows}
    else:
        return rows


def get_scalar(query, params=None):
    # Connect to the database
    conn = sqlite3.connect(db_path)

    # Create a cursor object
    cursor = conn.cursor()

    # Execute the query
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    # Fetch the first row
    row = cursor.fetchone()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    if row is None: return None
    # Return the first column of the first row
    return row[0]