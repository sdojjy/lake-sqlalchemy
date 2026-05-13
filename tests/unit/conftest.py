from unittest import mock
from tidbcloudlake_sqlalchemy import tidbcloudlake_dialect
from pytest import fixture


class MockDBApi:
    class DatabaseError:
        pass

    class Error:
        pass

    class IntegrityError:
        pass

    class NotSupportedError:
        pass

    class OperationalError:
        pass

    class ProgrammingError:
        pass

    paramstyle = ""

    def execute():
        pass

    def executemany():
        pass

    def connect():
        pass


class MockCursor:
    def execute():
        pass

    def executemany():
        pass

    def fetchall():
        pass

    def close():
        pass


@fixture
def dialect() -> tidbcloudlake_dialect.TiDBCloudLakeDialect:
    return tidbcloudlake_dialect.TiDBCloudLakeDialect()


@fixture
def connection() -> mock.Mock(spec=MockDBApi):
    return mock.Mock(spec=MockDBApi)


@fixture
def cursor() -> mock.Mock(spec=MockCursor):
    return mock.Mock(spec=MockCursor)
