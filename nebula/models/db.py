import psycopg2
import psycopg2.extras
from flask import g
from nebula import app
from psycopg2.extensions import STATUS_BEGIN, STATUS_READY


def get_conn():
    conn = getattr(g, '_database', None)
    if conn is None:
        g._database = psycopg2.connect(database=app.config['DB'], user=app.config['DB_USERNAME'],
                         password=app.config['DB_PASSWORD'], host=app.config['DB_HOST'])
    return g._database


def get_cursor():
    conn = get_conn()
    return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


def runQuery(query, params= None, commit = True):
    conn = get_conn()
    if (conn.status == STATUS_BEGIN): #Note: this read like it might cause weird race condition
        conn.rollback()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if (params is not None):
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    if commit:
        conn.commit()

    return cursor


def find_one(query, params = None):
    return runQuery(query, params).fetchone()


def find_one_dict(query, params = None):
    results = find_all_dict(query, params)

    if len(results) > 0:
        return results[0]

    return False


def find_all(query, params = None):
    return runQuery(query, params).fetchall()


def find_all_dict(query, params = None):
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if (params is not None):
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    columns = [column[0] for column in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))

    return results


def insert_and_get_id(query, params, commit = True):
    conn = get_conn()
    cursor = get_cursor()
    cursor.execute(query, params)
    ret = cursor.fetchone()
    if len(ret) < 1:
        return False

    if commit:
        conn.commit()

    return ret[0]


def execute(query, params = None):
    runQuery(query, params)
