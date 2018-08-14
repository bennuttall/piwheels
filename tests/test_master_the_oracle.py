# The piwheels project
#   Copyright (c) 2017 Ben Nuttall <https://github.com/bennuttall>
#   Copyright (c) 2017 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import pickle
from datetime import timedelta

import zmq
import pytest

from piwheels import const
from piwheels.master.db import Database
from piwheels.master.seraph import Seraph
from piwheels.master.the_oracle import TheOracle, DbClient


@pytest.fixture(scope='function')
def db_client(request, task_seraph, task_the_oracle, master_config):
    client = DbClient(master_config)
    return client


@pytest.fixture(scope='function')
def seraph_oracle_queue(request, zmq_context):
    queue = zmq_context.socket(zmq.REP)
    def fin():
        queue.close()
    request.addfinalizer(fin)
    queue.hwm = 10
    queue.bind(const.ORACLE_QUEUE)
    return queue


def test_oracle_init(seraph_oracle_queue, task_the_oracle):
    assert seraph_oracle_queue.recv() == b'READY'


def test_oracle_bad_request(seraph_oracle_queue, task_the_oracle):
    assert seraph_oracle_queue.recv() == b'READY'
    seraph_oracle_queue.send_multipart([b'foo', b'', pickle.dumps(['FOO'])])
    address, empty, resp = seraph_oracle_queue.recv_multipart()
    assert address == b'foo'
    assert empty == b''
    assert pickle.loads(resp) == ['ERR', repr('FOO')]


def test_db_get_all_packages(db_client, db, with_package):
    assert db_client.get_all_packages() == {'foo'}


def test_db_get_all_package_versions(db_client, db, with_package_version):
    assert db_client.get_all_package_versions() == {('foo', '0.1')}


def test_db_add_new_package(db_client, db, with_schema):
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM packages").first() == (0,)
    db_client.add_new_package('foo')
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM packages").first() == (1,)
        assert db.execute(
            "SELECT package, skip FROM packages").first() == ('foo', False)


def test_db_add_new_package_version(db_client, db, with_package):
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM versions").first() == (0,)
    db_client.add_new_package_version('foo', '0.1')
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM versions").first() == (1,)
        assert db.execute(
            "SELECT package, version, skip "
            "FROM versions").first() == ('foo', '0.1', False)


def test_db_skip_package(db_client, db, with_package):
    with db.begin():
        assert db.execute(
            "SELECT package, skip FROM packages").first() == ('foo', False)
    db_client.skip_package('foo')
    with db.begin():
        assert db.execute(
            "SELECT package, skip FROM packages").first() == ('foo', True)


def test_db_skip_package_version(db_client, db, with_package_version):
    with db.begin():
        assert db.execute(
            "SELECT package, version, skip "
            "FROM versions").first() == ('foo', '0.1', False)
    db_client.skip_package_version('foo', '0.1')
    with db.begin():
        assert db.execute(
            "SELECT package, version, skip "
            "FROM versions").first() == ('foo', '0.1', True)


def test_test_package_version(db_client, db, with_package_version):
    assert db_client.test_package_version('foo', '0.1')
    assert not db_client.test_package_version('foo', '0.2')


def test_db_log_download(db_client, db, with_files, download_state):
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM downloads").first() == (0,)
    db_client.log_download(download_state)
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM downloads").first() == (1,)
        assert db.execute(
            "SELECT filename FROM downloads").first() == (download_state.filename,)


def test_db_log_build(db_client, db, with_package_version, build_state_hacked):
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM builds").first() == (0,)
    db_client.log_build(build_state_hacked)
    assert build_state_hacked.build_id is not None
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM builds").first() == (1,)
        assert db.execute("SELECT COUNT(*) FROM files").first() == (2,)


def test_db_delete_build(db_client, db, with_build):
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM builds").first() == (1,)
    db_client.delete_build('foo', '0.1')
    with db.begin():
        assert db.execute("SELECT COUNT(*) FROM builds").first() == (0,)


def test_get_package_files(db_client, db, with_files, build_state_hacked):
    assert {
        (r.filename, r.filehash)
        for r in db_client.get_package_files('foo')
    } == {
        (r.filename, r.filehash)
        for r in build_state_hacked.files.values()
    }


def test_get_version_files(db_client, db, with_files, build_state_hacked):
    assert db_client.get_version_files('foo', '0.1') == build_state_hacked.files.keys()


def test_get_build_abis(db_client, db, with_build_abis):
    assert db_client.get_build_abis() == {'cp34m', 'cp35m'}


def test_get_pypi_serial(db_client, db, with_schema):
    assert db_client.get_pypi_serial() == 0


def test_set_pypi_serial(db_client, db, with_schema):
    assert db_client.get_pypi_serial() == 0
    db_client.set_pypi_serial(50000)
    assert db_client.get_pypi_serial() == 50000


def test_get_statistics(db_client, db, with_files):
    assert db_client.get_statistics() == (
        1, 1, 1, 1, 1, 1, 0, timedelta(minutes=5), 2, 123456, 0
    )
    assert db_client.stats_type is not None
    # Run twice to cover caching of Statstics type
    assert db_client.get_statistics() == (
        1, 1, 1, 1, 1, 1, 0, timedelta(minutes=5), 2, 123456, 0
    )


@pytest.mark.xfail(reason="downloads_recent view needs fixing")
def test_get_downloads_recent(db_client, db, with_downloads):
    assert db_client.get_downloads_recent() == {'foo': 0}


def test_bogus_request(db_client, db):
    with pytest.raises(IOError):
        db_client._execute(['FOO'])