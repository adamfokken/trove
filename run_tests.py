import gettext
import os
import urllib
import sys
import traceback

from trove.common import cfg
from trove.openstack.common import log as logging
from trove.tests.config import CONFIG
from wsgi_intercept.httplib2_intercept import install as wsgi_install
import proboscis
import wsgi_intercept
from trove.openstack.common.rpc import service as rpc_service

import eventlet
eventlet.monkey_patch(thread=False)

CONF = cfg.CONF


def add_support_for_localization():
    """Adds support for localization in the logging.

    If ../nova/__init__.py exists, add ../ to Python search path, so that
    it will override what happens to be installed in
    /usr/(local/)lib/python...

    """
    path = os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir)
    possible_topdir = os.path.normpath(path)
    if os.path.exists(os.path.join(possible_topdir, 'nova', '__init__.py')):
        sys.path.insert(0, possible_topdir)

    gettext.install('nova', unicode=1)


def initialize_trove(config_file):
    from trove.openstack.common import pastedeploy

    cfg.CONF(args=[],
             project='trove',
             default_config_files=[config_file])
    logging.setup(None)
    topic = CONF.taskmanager_queue

    from trove.taskmanager import manager
    manager_impl = manager.Manager()
    taskman_service = rpc_service.Service(None, topic=topic,
                                          manager=manager_impl)
    taskman_service.start()

    return pastedeploy.paste_deploy_app(config_file, 'trove', {})


def datastore_init():
    # Adds the datastore for mysql (needed to make most calls work).
    from trove.datastore import models
    models.DBDatastore.create(id="a00000a0-00a0-0a00-00a0-000a000000aa",
                              name=CONFIG.dbaas_datastore, manager='mysql',
                              default_version_id=
                              "b00000b0-00b0-0b00-00b0-000b000000bb")
    models.DBDatastore.create(id="e00000e0-00e0-0e00-00e0-000e000000ee",
                              name='Test_Datastore_1', manager='manager1',
                              default_version_id=None)
    models.DBDatastoreVersion.create(id="b00000b0-00b0-0b00-00b0-000b000000bb",
                                     datastore_id=
                                     "a00000a0-00a0-0a00-00a0-000a000000aa",
                                     name=CONFIG.dbaas_datastore_version,
                                     image_id=
                                     'c00000c0-00c0-0c00-00c0-000c000000cc',
                                     packages='test packages',
                                     active=1)
    models.DBDatastoreVersion.create(id="d00000d0-00d0-0d00-00d0-000d000000dd",
                                     datastore_id=
                                     "a00000a0-00a0-0a00-00a0-000a000000aa",
                                     name='mysql_inactive_version',
                                     image_id=
                                     'c00000c0-00c0-0c00-00c0-000c000000cc',
                                     packages=None, active=0)


def initialize_database():
    from trove.db import get_db_api
    from trove.db.sqlalchemy import session
    db_api = get_db_api()
    db_api.drop_db(CONF)  # Destroys the database, if it exists.
    db_api.db_sync(CONF)
    session.configure_db(CONF)
    datastore_init()
    db_api.configure_db(CONF)


def initialize_fakes(app):
    # Set up WSGI interceptor. This sets up a fake host that responds each
    # time httplib tries to communicate to localhost, port 8779.
    def wsgi_interceptor(*args, **kwargs):

        def call_back(env, start_response):
            path_info = env.get('PATH_INFO')
            if path_info:
                env['PATH_INFO'] = urllib.unquote(path_info)
            #print("%s %s" % (args, kwargs))
            return app.__call__(env, start_response)

        return call_back

    wsgi_intercept.add_wsgi_intercept('localhost',
                                      CONF.bind_port,
                                      wsgi_interceptor)
    from trove.tests.util import event_simulator
    event_simulator.monkey_patch()


def parse_args_for_test_config():
    for index in range(len(sys.argv)):
        arg = sys.argv[index]
        print(arg)
        if arg[:14] == "--test-config=":
            del sys.argv[index]
            return arg[14:]
    return 'etc/tests/localhost.test.conf'

if __name__ == "__main__":
    try:
        wsgi_install()
        add_support_for_localization()
        # Load Trove app
        # Paste file needs absolute path
        config_file = os.path.realpath('etc/trove/trove.conf.test')
        # 'etc/trove/test-api-paste.ini'
        app = initialize_trove(config_file)
        # Initialize sqlite database.
        initialize_database()
        # Swap out WSGI, httplib, and several sleep functions
        # with test doubles.
        initialize_fakes(app)

        # Initialize the test configuration.
        test_config_file = parse_args_for_test_config()
        CONFIG.load_from_file(test_config_file)

        from trove.tests.api import backups
        from trove.tests.api import header
        from trove.tests.api import limits
        from trove.tests.api import flavors
        from trove.tests.api import versions
        from trove.tests.api import instances as rd_instances
        from trove.tests.api import instances_actions as rd_actions
        from trove.tests.api import instances_delete
        from trove.tests.api import instances_mysql_down
        from trove.tests.api import instances_resize
        from trove.tests.api import databases
        from trove.tests.api import datastores
        from trove.tests.api import root
        from trove.tests.api import root_on_create
        from trove.tests.api import users
        from trove.tests.api import user_access
        from trove.tests.api.mgmt import accounts
        from trove.tests.api.mgmt import admin_required
        from trove.tests.api.mgmt import hosts
        from trove.tests.api.mgmt import instances as mgmt_instances
        from trove.tests.api.mgmt import instances_actions as mgmt_actions
        from trove.tests.api.mgmt import storage
        from trove.tests.api.mgmt import malformed_json
    except Exception as e:
        print("Run tests failed: %s" % e)
        traceback.print_exc()
        raise

    proboscis.TestProgram().run_and_exit()
