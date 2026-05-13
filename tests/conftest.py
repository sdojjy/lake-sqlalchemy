from sqlalchemy.dialects import registry
import pytest

registry.register("tidbcloudlake.tidbcloudlake", "tidbcloudlake_sqlalchemy.tidbcloudlake_dialect", "TiDBCloudLakeDialect")
registry.register("tidbcloudlake", "tidbcloudlake_sqlalchemy.tidbcloudlake_dialect", "TiDBCloudLakeDialect")

pytest.register_assert_rewrite("sa.testing.assertions")

from sqlalchemy.testing.plugin.pytestplugin import *

from packaging import version
import sqlalchemy
if version.parse(sqlalchemy.__version__) >= version.parse('2.0.0'):
    from sqlalchemy import event, text
    from sqlalchemy import Engine

    @event.listens_for(Engine, "connect")
    def receive_engine_connect(conn, r):
        cur = conn.cursor()
        cur.execute('SET global format_null_as_str = 0')
        cur.execute('SET global enable_geo_create_table = 1')
        try:
            cur.execute("SET global sequence_step_size = 1")
        except:
            pass # don't fail when this setting doesn't exist
        cur.close()
