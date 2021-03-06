#
# Copyright (c) 2017 Juniper Networks, Inc. All rights reserved.
#
import gevent.monkey
gevent.monkey.patch_all()  # noqa
import logging
from testtools import ExpectedException

from cfgm_common import VNID_MIN_ALLOC
from cfgm_common.exceptions import PermissionDenied
from vnc_api.vnc_api import VirtualNetwork

import test_case


logger = logging.getLogger(__name__)


class TestVirtualNetworkBase(test_case.ApiServerTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.console_handler = logging.StreamHandler()
        cls.console_handler.setLevel(logging.DEBUG)
        logger.addHandler(cls.console_handler)
        super(TestVirtualNetworkBase, cls).setUpClass(*args, **kwargs)

    @classmethod
    def tearDownClass(cls, *args, **kwargs):
        logger.removeHandler(cls.console_handler)
        super(TestVirtualNetworkBase, cls).tearDownClass(*args, **kwargs)

    @property
    def api(self):
        return self._vnc_lib


class TestVirtualNetwork(TestVirtualNetworkBase):
    def test_allocate_vn_id(self):
        mock_zk = self._api_server._db_conn._zk_db
        vn_obj = VirtualNetwork('%s-vn' % self.id())

        self.api.virtual_network_create(vn_obj)

        vn_obj = self.api.virtual_network_read(id=vn_obj.uuid)
        vn_id = vn_obj.virtual_network_network_id
        self.assertEqual(vn_obj.get_fq_name_str(),
                         mock_zk.get_vn_from_id(vn_id))
        self.assertGreaterEqual(vn_id, VNID_MIN_ALLOC)

    def test_deallocate_vn_id(self):
        mock_zk = self._api_server._db_conn._zk_db
        vn_obj = VirtualNetwork('%s-vn' % self.id())
        self.api.virtual_network_create(vn_obj)
        vn_obj = self.api.virtual_network_read(id=vn_obj.uuid)
        vn_id = vn_obj.virtual_network_network_id

        self.api.virtual_network_delete(id=vn_obj.uuid)

        self.assertNotEqual(mock_zk.get_vn_from_id(vn_id),
                            vn_obj.get_fq_name_str())

    def test_not_deallocate_vn_id_if_fq_name_does_not_correspond(self):
        mock_zk = self._api_server._db_conn._zk_db
        vn_obj = VirtualNetwork('%s-vn' % self.id())
        self.api.virtual_network_create(vn_obj)
        vn_obj = self.api.virtual_network_read(id=vn_obj.uuid)
        vn_id = vn_obj.virtual_network_network_id

        fake_fq_name = "fake fq_name"
        mock_zk._vn_id_allocator.delete(vn_id - VNID_MIN_ALLOC)
        mock_zk._vn_id_allocator.reserve(vn_id - VNID_MIN_ALLOC, fake_fq_name)
        self.api.virtual_network_delete(id=vn_obj.uuid)

        self.assertIsNotNone(mock_zk.get_vn_from_id(vn_id))
        self.assertEqual(fake_fq_name, mock_zk.get_vn_from_id(vn_id))

    def test_cannot_set_vn_id(self):
        vn_obj = VirtualNetwork('%s-vn' % self.id())
        vn_obj.set_virtual_network_network_id(42)

        with ExpectedException(PermissionDenied):
            self.api.virtual_network_create(vn_obj)

    def test_cannot_update_vn_id(self):
        vn_obj = VirtualNetwork('%s-vn' % self.id())
        self.api.virtual_network_create(vn_obj)
        vn_obj = self.api.virtual_network_read(id=vn_obj.uuid)

        vn_obj.set_virtual_network_network_id(42)
        with ExpectedException(PermissionDenied):
            self.api.virtual_network_update(vn_obj)

        # test can update with same value, needed internally
        # TODO(ethuleau): not sure why it's needed
        vn_obj = self.api.virtual_network_read(id=vn_obj.uuid)
        vn_obj.set_virtual_network_network_id(
            vn_obj.virtual_network_network_id)
        self.api.virtual_network_update(vn_obj)
