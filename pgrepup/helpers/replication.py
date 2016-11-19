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
from database import *
from time import sleep
from psycopg2 import Error
from psycopg2 import extras

def check_destination_subscriptions():
    """Return True if there are active subscriptions in destination database"""

    result = False
    subscriptions = get_destination_subscriptions()
    for s in iter(subscriptions.keys()):
        result = result or subscriptions[s]
    return result


def get_destination_subscriptions():
    """Return hash with dbname and boolean as value (True if subscription is in progress)"""

    result = {}
    conn = connect('Destination')
    for db in get_cluster_databases(conn):
        db_conn = connect('Destination', db_name=db)
        result[db] = False
        try:
            cur = db_conn.cursor()
            cur.execute("SELECT status FROM pglogical.show_subscription_status(subscription_name := 'subscription');")
            for r in cur.fetchall():
                if r[0] == 'replicating' or 'down':
                    result[db] = True
        except psycopg2.InternalError:
            result[db] = False
        except psycopg2.OperationalError:
            result[db] = False
        except psycopg2.ProgrammingError:
            result[db] = False

    return result


def stop_subscription(db):
    """Stop subscription in given database. Return True if success"""
    db_conn = connect('Destination', db_name=db)
    db_conn.autocommit = True
    cur = db_conn.cursor()
    while True:
        cur.execute("SELECT * FROM pglogical.drop_subscription(subscription_name := %s, ifexists := false)",
                    ['subscription'])
        if cur.fetchone()[0] == 0:
            break
        sleep(1)

    return True


def drop_node(db):
    """Stop all background workers of pglogical"""

    db_conn = connect('Destination', db_name=db)
    db_conn.autocommit = True
    cur = db_conn.cursor()
    while True:
        try:
            cur.execute("SELECT * FROM pglogical.drop_node(node_name := 'Destination', ifexists := false);")
        except psycopg2.ProgrammingError:
            break
        if not cur.fetchone()[0]:
            break
        sleep(1)


def start_subscription(db):
    db_conn = connect('Destination', db)
    db_conn.autocommit = True
    c = db_conn.cursor()
    c.execute(
        """
        SELECT pglogical.create_subscription(
                                subscription_name := 'subscription',
                                provider_dsn := %s,
                                replication_sets := '{default}'::text[]
        );
        """,
        [get_dsn_for_pglogical('Source', db)]
    )


def syncronize_sequences(db):
    db_conn = connect('Source', db)
    db_conn.autocommit = True
    c = db_conn.cursor()
    c.execute("SELECT pglogical.synchronize_sequence( seqoid ) FROM pglogical.sequence_state")


def setup_ddl_syncronization(db):
    """
    Create a trigger on CREATE TABLE/SEQUENCE events in order to replicate them to the Destination Database

    :param db:
    :return: boolean
    """
    db_conn = connect('Source', db)
    try:
        schemas = get_schemas(db_conn)

        c = db_conn.cursor()
        c.execute("DROP event trigger IF EXISTS trg_pgrepup_replicate_ddl;")
        c.execute("""
CREATE OR REPLACE FUNCTION pgrepup_replicate_ddl()
RETURNS event_trigger AS $$
DECLARE obj record;
BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() where command_tag in ('CREATE TABLE', 'CREATE TABLE AS', 'CREATE SEQUENCE')
    LOOP
        IF obj.schema_name = ANY(%s) AND NOT obj.in_extension THEN
            IF obj.object_type = 'table' THEN
                PERFORM pglogical.replication_set_add_table('default', obj.objid);
            ELSIF obj.object_type = 'sequence' THEN
                PERFORM pglogical.replication_set_add_sequence('default', obj.objid);
            END IF;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
        """, [schemas])

        c.execute("""
CREATE EVENT TRIGGER trg_pgrepup_replicate_ddl ON ddl_command_end
WHEN TAG IN ('CREATE TABLE', 'CREATE TABLE AS', 'CREATE SEQUENCE') EXECUTE PROCEDURE pgrepup_replicate_ddl();
        """)

        db_conn.commit()
        return True
    except:
        db_conn.rollback()
        return False


def create_replication_sets(db):
    db_conn = connect('Source', db)
    if not db_conn:
        return False

    try:
        db_schemas = get_schemas(db_conn)
        c = db_conn.cursor()
        c.execute("CREATE EXTENSION pglogical")
        c.execute("SELECT pglogical.drop_node(node_name := %s, ifexists := false)", ['Source'])
        c.execute("SELECT pglogical.create_node(node_name := %s, dsn := %s );",
                  ['Source', get_dsn_for_pglogical('Source', db_name=db)])
        c.execute("SELECT pglogical.replication_set_add_all_tables('default', '{%s}'::text[]);" % ','.join(db_schemas))
        c.execute("SELECT pglogical.replication_set_add_all_sequences( set_name := 'default', schema_names := %s)",
                  [db_schemas])
        db_conn.commit()
        return True
    except:
        db_conn.rollback()
        return False


def clean_pglogical_setup(db):
    db_conn = connect('Source', db)
    db_conn.autocommit = True
    if not db_conn:
        return False
    if not drop_extension(db_conn, "pglogical"):
        return False

    c = db_conn.cursor()
    c.execute("DROP event trigger IF EXISTS trg_pgrepup_replicate_ddl;")
    c.execute("DROP FUNCTION IF EXISTS pgrepup_replicate_ddl()")

    return True


def create_pglogical_node(db):
    db_conn = connect('Destination', db)
    if not db_conn:
        return False;

    try:
        c = db_conn.cursor()
        drop_extension(db_conn, "pglogical")
        c.execute("DROP SCHEMA IF EXISTS pglogical CASCADE")
        c.execute("CREATE EXTENSION pglogical")
        c.execute("SELECT pglogical.drop_node(node_name := %s, ifexists := false)", ['Destination'])
        c.execute("SELECT pglogical.create_node( node_name := %s, dsn := %s );", [
            'Destination', get_dsn_for_pglogical('Destination', db)
        ])
        db_conn.commit()
    except Error:
        db_conn.rollback()
        return False

    return True


def store_setup_result(target, db, result):
    db_conn = connect(target, db)
    if not db_conn:
        return False

    try:
        c = db_conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS pglogical.pgrepup_setup(result BOOL NOT NULL PRIMARY KEY)")
        c.execute("TRUNCATE pglogical.pgrepup_setup")
        c.execute("INSERT INTO pglogical.pgrepup_setup VALUES (%s)", [result])
        db_conn.commit()
    except Error:
        db_conn.rollback()
        return False

    return True


def get_setup_result(target, db):
    db_conn = connect(target, db)
    db_conn.autocommit = True
    if not db_conn:
        return False
    try:
        c = db_conn.cursor()
        c.execute("SELECT result FROM pglogical.pgrepup_setup")
        r = c.fetchone()
        if len(r) != 1:
            return False
        return r[0]

    except Error:
        return False


def get_replication_status(db):
    result = {"result": False, "status": None}
    db_conn = connect('Destination', db_name=db)
    src_db_conn = connect('Source', db_name=db)
    result["result"] = False
    try:
        cur = db_conn.cursor(cursor_factory=extras.DictCursor)
        cur.execute("SELECT status FROM pglogical.show_subscription_status(subscription_name := 'subscription');")
        r = cur.fetchone()
        if r:
            result["result"] = True
            result["status"] = r['status']

    except psycopg2.InternalError:
        result["result"] = False
    except psycopg2.OperationalError:
        result["result"] = False
    except psycopg2.ProgrammingError:
        result["result"] = False

    return result


def get_replication_delay():
    db_conn = connect('Destination')
    src_db_conn = connect('Source')
    dest_cur = db_conn.cursor()
    src_cur = src_db_conn.cursor()

    dest_cur.execute("SELECT remote_lsn FROM pg_replication_origin_status ORDER BY remote_lsn DESC limit 1;")
    d_lsn_r = dest_cur.fetchone()
    if d_lsn_r:
        src_cur.execute("SELECT pg_xlog_location_diff(pg_current_xlog_location(), %s)", [d_lsn_r[0]])
        diff = src_cur.fetchone()
        return diff
    else:
        return False
