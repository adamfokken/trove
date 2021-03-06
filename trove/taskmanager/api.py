# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""
Routes all the requests to the task manager.
"""


from trove.common import cfg
from trove.openstack.common.rpc import proxy
from trove.openstack.common import log as logging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)
RPC_API_VERSION = "1.0"


class API(proxy.RpcProxy):
    """API for interacting with the task manager."""

    def __init__(self, context):
        self.context = context
        super(API, self).__init__(self._get_routing_key(),
                                  RPC_API_VERSION)

    def _transform_obj(self, obj_ref):
        # Turn the object into a dictionary and remove the mgr
        if "__dict__" in dir(obj_ref):
            obj_dict = obj_ref.__dict__
            # We assume manager contains a object due to the *clients
            if obj_dict.get('manager'):
                del obj_dict['manager']
            return obj_dict
        raise ValueError("Could not transform %s" % obj_ref)

    def _get_routing_key(self):
        """Create the routing key for the taskmanager"""
        return CONF.taskmanager_queue

    def resize_volume(self, new_size, instance_id):
        LOG.debug("Making async call to resize volume for instance: %s"
                  % instance_id)
        self.cast(self.context, self.make_msg("resize_volume",
                                              new_size=new_size,
                                              instance_id=instance_id))

    def resize_flavor(self, instance_id, old_flavor, new_flavor):
        LOG.debug("Making async call to resize flavor for instance: %s" %
                  instance_id)
        self.cast(self.context,
                  self.make_msg("resize_flavor",
                                instance_id=instance_id,
                                old_flavor=self._transform_obj(old_flavor),
                                new_flavor=self._transform_obj(new_flavor)))

    def reboot(self, instance_id):
        LOG.debug("Making async call to reboot instance: %s" % instance_id)
        self.cast(self.context,
                  self.make_msg("reboot", instance_id=instance_id))

    def restart(self, instance_id):
        LOG.debug("Making async call to restart instance: %s" % instance_id)
        self.cast(self.context,
                  self.make_msg("restart", instance_id=instance_id))

    def migrate(self, instance_id, host):
        LOG.debug("Making async call to migrate instance: %s" % instance_id)
        self.cast(self.context,
                  self.make_msg("migrate", instance_id=instance_id, host=host))

    def delete_instance(self, instance_id):
        LOG.debug("Making async call to delete instance: %s" % instance_id)
        self.cast(self.context,
                  self.make_msg("delete_instance", instance_id=instance_id))

    def create_backup(self, backup_id, instance_id):
        LOG.debug("Making async call to create a backup for instance: %s" %
                  instance_id)
        self.cast(self.context, self.make_msg("create_backup",
                                              backup_id=backup_id,
                                              instance_id=instance_id))

    def delete_backup(self, backup_id):
        LOG.debug("Making async call to delete backup: %s" % backup_id)
        self.cast(self.context, self.make_msg("delete_backup",
                                              backup_id=backup_id))

    def create_instance(self, instance_id, name, flavor,
                        image_id, databases, users, datastore_manager,
                        packages, volume_size, backup_id=None,
                        availability_zone=None, root_password=None):
        LOG.debug("Making async call to create instance %s " % instance_id)
        self.cast(self.context,
                  self.make_msg("create_instance",
                                instance_id=instance_id, name=name,
                                flavor=self._transform_obj(flavor),
                                image_id=image_id,
                                databases=databases,
                                users=users,
                                datastore_manager=datastore_manager,
                                packages=packages,
                                volume_size=volume_size,
                                backup_id=backup_id,
                                availability_zone=availability_zone,
                                root_password=root_password))
