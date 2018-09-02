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


from unittest import mock
from collections import namedtuple
from datetime import datetime, timedelta

import zmq
import pytest

from conftest import MockTask
from piwheels import const
from piwheels.master.big_brother import BigBrother


@pytest.fixture()
def stats_result(request):
    return [
        ('packages_count',         1),
        ('packages_built',         0),
        ('versions_count',         2),
        ('versions_tried',         0),
        ('builds_count',           0),
        ('builds_count_success',   0),
        ('builds_count_last_hour', 0),
        ('builds_time',            timedelta(0)),
        ('files_count',            0),
        ('builds_size',            0),
        ('downloads_last_month',   10),
    ]


@pytest.fixture()
def stats_dict(request):
    return {
        'packages_count': 1,
        'packages_built': 0,
        'versions_count': 2,
        'builds_count':   0,
        'builds_last_hour': 0,
        'builds_success': 0,
        'builds_time': timedelta(0),
        'builds_size': 0,
        'builds_pending': 0,
        'files_count': 0,
        'disk_free': 0,
        'disk_size': 1,
        'downloads_last_month': 10,
    }


StatVFS = namedtuple('StatVFS', (
    'f_bsize',
    'f_frsize',
    'f_blocks',
    'f_bfree',
    'f_bavail',
    'f_files',
    'f_ffree',
    'f_favail',
    'f_flag',
    'f_namemax',
))


@pytest.fixture()
def stats_disk(request):
    return StatVFS(
        4096, 4096, 1000000, 50000, 40000, 1000000, 500000, 500000, 4096,
        255)


@pytest.fixture()
def stats_queue(request, zmq_context, master_config):
    queue = zmq_context.socket(zmq.PUSH)
    queue.hwm = 1
    queue.connect(master_config.stats_queue)
    yield queue
    queue.close()


@pytest.fixture()
def task(request, master_config):
    task = BigBrother(master_config)
    yield task
    task.close()


def test_gen_stats(db_queue, master_status_queue, index_queue, task,
                   stats_result, stats_dict):
    with mock.patch('piwheels.master.big_brother.datetime') as dt:
        dt.utcnow.return_value = datetime(2018, 1, 1, 12, 30, 40)
        task.timestamp = datetime(2018, 1, 1, 12, 30, 0)
        db_queue.expect(['GETSTATS'])
        db_queue.send(['OK', stats_result])
        index_queue.expect(['HOME', stats_dict])
        master_status_queue.expect([-1, dt.utcnow.return_value, 'STATUS', stats_dict])
        db_queue.expect(['GETDL'])
        db_queue.send(['OK', {'foo': 10}])
        index_queue.expect(['SEARCH', [('foo', 10)]])
        task.loop()  # crank the handle once
        db_queue.check()
        index_queue.check()
        master_status_queue.check()


def test_gen_disk_stats(db_queue, master_status_queue, index_queue, task,
                        stats_queue, stats_result, stats_dict, stats_disk):
    with mock.patch('piwheels.master.big_brother.datetime') as dt:
        dt.utcnow.return_value = datetime(2018, 1, 1, 12, 30, 40)
        task.timestamp = datetime(2018, 1, 1, 12, 30, 0)
        stats_queue.send_pyobj(['STATFS', stats_disk])
        while task.stats['disk_free'] == 0:
            task.poll()
        stats_dict['disk_free'] = stats_disk.f_frsize * stats_disk.f_bavail
        stats_dict['disk_size'] = stats_disk.f_frsize * stats_disk.f_blocks
        db_queue.expect(['GETSTATS'])
        db_queue.send(['OK', stats_result])
        index_queue.expect(['HOME', stats_dict])
        master_status_queue.expect([-1, dt.utcnow.return_value, 'STATUS', stats_dict])
        db_queue.expect(['GETDL'])
        db_queue.send(['OK', {'foo': 10}])
        index_queue.expect(['SEARCH', [('foo', 10)]])
        task.loop()
        db_queue.check()
        index_queue.check()
        master_status_queue.check()


def test_gen_queue_stats(db_queue, master_status_queue, index_queue, task,
                         stats_queue, stats_result, stats_dict):
    with mock.patch('piwheels.master.big_brother.datetime') as dt:
        dt.utcnow.return_value = datetime(2018, 1, 1, 12, 30, 40)
        task.timestamp = datetime(2018, 1, 1, 12, 30, 0)
        stats_queue.send_pyobj(['STATBQ', {'cp34m': 1, 'cp35m': 0}])
        while task.stats['builds_pending'] == 0:
            task.poll()
        stats_dict['builds_pending'] = 1
        db_queue.expect(['GETSTATS'])
        db_queue.send(['OK', stats_result])
        index_queue.expect(['HOME', stats_dict])
        master_status_queue.expect([-1, dt.utcnow.return_value, 'STATUS', stats_dict])
        db_queue.expect(['GETDL'])
        db_queue.send(['OK', {'foo': 10}])
        index_queue.expect(['SEARCH', [('foo', 10)]])
        task.loop()
        db_queue.check()
        index_queue.check()
        master_status_queue.check()


def test_bad_stats(db_queue, master_status_queue, index_queue, task,
                         stats_queue, stats_result, stats_dict):
    task.logger = mock.Mock()
    with mock.patch('piwheels.master.big_brother.datetime') as dt:
        dt.utcnow.return_value = datetime(2018, 1, 1, 12, 30, 40)
        task.timestamp = datetime(2018, 1, 1, 12, 30, 0)
        stats_queue.send_pyobj(['FOO'])
        while task.logger.error.call_count == 0:
            task.poll()
        assert task.logger.error.call_args == mock.call(
            'invalid big_brother message: %s', 'FOO')