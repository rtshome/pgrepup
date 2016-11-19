# Copyright (C) 2016 Denis Gasparin <denis@gasparin.net>
#
# This file is part of Pgrepup.
#
# Pgrepup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pgrepup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pgrepup. If not, see <http://www.gnu.org/licenses/>.
import hashlib
import os
import psycopg2
import uuid
try:  # Python 2
    import ConfigParser
except ImportError:  # Python 3
    import configparser

from ..config import config
from ..config import save as save_config
from ..config import get_tmp_folder
from ..helpers.crypt import decrypt
from ..helpers.crypt import encrypt


def get_dsn(database, db_name=None):
    return "host=%(host)s port=%(port)s dbname=%(dbname)s user=%(user)s password=%(password)s" \
           % get_connection_params(database, db_name)


def get_connection_params(database, db_name=None):
    return {
        "host": config().get(database, 'host'),
        "port": config().get(database, 'port'),
        "user": config().get(database, 'user'),
        "password": decrypt(config().get(database, 'password')),
        "dbname": db_name if db_name else config().get(database, 'connect_database'),
    }


def get_dsn_for_pglogical(database, db_name):
    params = get_connection_params(database, db_name)
    params['user'] = get_pgrepup_replication_user()
    params['password'] = get_pgrepup_user_password()
    return "host=%(host)s port=%(port)s dbname=%(dbname)s user=%(user)s password=%(password)s" \
           % params


def connect(database, db_name=None):
    try:
        conn = psycopg2.connect(get_dsn(database, db_name))
        return conn
    except psycopg2.DatabaseError:
        return None


def get_database_count(conn):
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pg_database WHERE datallowconn='t';")
        return cur.fetchone()[0]
    except psycopg2.Error:
        return None


def get_cluster_databases(conn):
    try:
        databases = []
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datallowconn='t';")
        for d in cur.fetchall():
            databases.append(d[0])
        return databases
    except psycopg2.Error:
        return None


def check_extension(conn, extension_name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM pg_extension WHERE extname = %s;", [extension_name])
    return True if cur.fetchone() else False


def create_extension(conn, extension_name, test=False):
    # The following error means that pglogical package is not installed into the operating system
    # ERROR:  could not open extension control file "/usr/share/postgresql/9.6/extension/pglogical.control":

    # The following error means that pglogical is installed but not configured correctly
    # ERROR:  pglogical is not in shared_preload_libraries
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS %s" % extension_name)
        if not test:
            conn.commit()
    except psycopg2.InternalError as e:
        msg = str(e)
        if msg.find('shared_preload_libraries'):
            return 'InstalledNoSharedLibraries'
        return 'NotInstalled'
    except psycopg2.OperationalError:
        return 'NotInstalled'
    finally:
        if test:
            conn.rollback()
    return True


def drop_extension(conn, extension_name):
    cur = conn.cursor()
    try:
        cur.execute("DROP EXTENSION IF EXISTS %s CASCADE" % extension_name)
        cur.execute("DROP SCHEMA IF EXISTS pglogical CASCADE")
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
    return True


def get_setting_value(conn, name):
    try:
        cur = conn.cursor()
        cur.execute("SELECT setting FROM pg_settings WHERE name=%s;", [name])
        return cur.fetchone()[0]
    except psycopg2.Error:
        return None


def get_pg_hba_contents(conn):
    pg_hba_path = get_setting_value(conn, "hba_file")
    if not pg_hba_path:
        return None

    try:
        temp_table = "pghba_" + uuid.uuid4().hex
        cur = conn.cursor()
        cur.execute("CREATE TEMP TABLE " + temp_table + " (content text)")
        cur.execute("COPY " + temp_table + " FROM %s", [pg_hba_path])
        cur.execute("SELECT * FROM " + temp_table +";")
        rows = cur.fetchall()
        conn.rollback()
        return rows
    except psycopg2.Error as e:
        print e
        return None


def get_pgrepup_replication_user():
    return "pgrepup_replication"


def get_pgrepup_user_password():
    try:
        config().get('Security', 'pg_repup_user_password')
    except ConfigParser.Error:
        config().set('Security', 'pg_repup_user_password', encrypt(uuid.uuid4().hex))
        save_config(print_save_result=False)
    finally:
        return decrypt(config().get('Security', 'pg_repup_user_password'))


def get_postgresql_version(conn):
    return get_setting_value(conn, 'server_version')


def create_user(conn, username, password):
    try:
        cur = conn.cursor()
        cur.execute("SELECT passwd FROM pg_shadow WHERE usename = %s", [username])
        row = cur.fetchone()
        if row:
            m = hashlib.md5()
            m.update(password + username)
            encrypted_password = "md5" + m.hexdigest()
            if encrypted_password != row[0]:
                cur.execute("ALTER USER " + username + " ENCRYPTED PASSWORD %s SUPERUSER REPLICATION", [password])
        else:
            cur.execute("CREATE USER " + username + " WITH ENCRYPTED PASSWORD %s SUPERUSER REPLICATION", [password])
        conn.commit()
        return True
    except psycopg2.Error as e:
        print e
        conn.rollback()
        return False


def drop_user(conn, username):
    try:
        cur = conn.cursor()
        cur.execute("SELECT passwd FROM pg_shadow WHERE usename = %s", [username])
        row = cur.fetchone()
        if row:
            cur.execute("DROP OWNED BY " + username + " CASCADE")
        cur.execute("DROP USER IF EXISTS " + username)
        conn.commit()
        return True
    except psycopg2.Error as e:
        print e
        conn.rollback()
        return False



def create_pgpass_file():
    fname = "%s/pgpass_repup" % get_tmp_folder()
    pgpass = open(fname, 'w')
    pgpass.writelines((
        # File format for pgpass: https://www.postgresql.org/docs/9.5/static/libpq-pgpass.html
        # hostname:port:database:username:password
        "%(host)s:%(port)s:*:%(user)s:%(password)s\n" % get_connection_params('Source'),
        "%(host)s:%(port)s:*:%(user)s:%(password)s\n" % get_connection_params('Destination')
    ))
    pgpass.close()
    os.chmod(fname, 0600)
    return fname


def remove_pgpass_file():
    fname = "%s/pgpass_repup" % get_tmp_folder()
    if not os.path.exists(fname):
        return True

    try:
        os.unlink(fname)
        return True
    except OSError:
        return False


def get_schemas(db_conn):
    c = db_conn.cursor()
    c.execute("""
SELECT n.nspname AS "Name", pg_catalog.pg_get_userbyid(n.nspowner) AS "Owner"
FROM pg_catalog.pg_namespace n
WHERE n.nspname !~ '^pg_|pglogical|information_schema'
ORDER BY 1;""")
    return [r[0] for r in c.fetchall()]
