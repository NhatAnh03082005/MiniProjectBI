"""TEST-only sessions with irreversible SQL principal reduction before use."""
import re
import pyodbc

SERVER = r'DESKTOP-OBDFK6B\SQLEXPRESS'
DATABASE = 'AmazonDeliveryBI_TEST'
LOGIN = 'AmazonDeliveryBI_TEST_Runtime'
CONNECTION = (r'DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost\SQLEXPRESS;'
              'DATABASE=AmazonDeliveryBI_TEST;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;')
_original_connect = pyodbc.connect


def restricted_connect(connection_string=CONNECTION, *args, **kwargs):
    # dbt-sqlserver sets this True immediately before connect. Reset it here:
    # NO REVERT sessions must never be handed back through sp_reset_connection.
    pyodbc.pooling = False
    connection_string = re.sub(r'(?i)Pooling=true', 'Pooling=false', connection_string)
    database = re.search(r'(?:DATABASE|INITIAL CATALOG)\s*=\s*\{?([^;}]+)', connection_string, re.I)
    server = re.search(r'(?:SERVER|DATA SOURCE)\s*=\s*\{?([^;}]+)', connection_string, re.I)
    if not database or database.group(1).strip() != DATABASE:
        raise RuntimeError('TEST connection database mismatch; no fallback permitted')
    if not server or server.group(1).strip().lower() not in {
        r'localhost\sqlexpress', r'.\sqlexpress', SERVER.lower()}:
        raise RuntimeError('TEST connection server mismatch')
    kwargs.setdefault('timeout', 5)
    connection = _original_connect(connection_string, *args, **kwargs)
    try:
        initial_autocommit = connection.autocommit
        connection.autocommit = True
        if connection.execute('SELECT SUSER_SNAME();').fetchone()[0] != LOGIN:
            connection.execute("EXECUTE AS LOGIN = 'AmazonDeliveryBI_TEST_Runtime' WITH NO REVERT;")
        actual = connection.execute('''SELECT CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),
            DB_NAME(),SUSER_SNAME(),IS_SRVROLEMEMBER('sysadmin'),HAS_DBACCESS('AmazonDeliveryBI');''').fetchone()
        if tuple(actual) != (SERVER, DATABASE, LOGIN, 0, 0):
            raise RuntimeError('TEST identity isolation verification failed')
        connection.execute('''SET LOCK_TIMEOUT 5000; SET QUOTED_IDENTIFIER ON;
            SET ANSI_NULLS ON; SET ANSI_PADDING ON; SET ANSI_WARNINGS ON;
            SET ARITHABORT ON; SET CONCAT_NULL_YIELDS_NULL ON; SET NUMERIC_ROUNDABORT OFF;''')
        connection.autocommit = initial_autocommit
        return connection
    except BaseException:
        connection.close()
        raise


def connect(autocommit=True):
    return restricted_connect(CONNECTION, autocommit=autocommit)


def install_process_guard():
    # Never return an elevated/pooled session to TEST application code.
    import os
    if os.environ.get('MSSQL_DATABASE') != DATABASE or os.environ.get('DBT_SQLSERVER_DATABASE') != DATABASE:
        raise RuntimeError('Explicit TEST environment required; primary fallback forbidden')
    pyodbc.pooling = False
    pyodbc.connect = restricted_connect
