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

"""
The piwheels project provides a set of tools for generating wheels from the
PyPI repository for a given set of Python ABIs. Currently, three scripts are
defined:

* ``piw-slave`` - this is the simple build slave script. Build slaves should be
  deployed using the ``deploy_slave.sh`` script from the source repository.
  This ensures that slaves are set up with a non-root user for building which
  has no write access to its own source code, and that common library
  dependencies for various builds are pre-installed.

* ``piw-master`` - this is the coordinating server script. It handles querying
  PyPI for packages to build, handing jobs to build slaves, receiving the
  results of builds, transferring files from build slaves, generating the
  package index, and keeping the PostgreSQL database up to date. In future this
  may be split into several scripts for performance or security reasons.

* ``piw-monitor`` - this is the curses-style monitoring client which can be run
  to watch the state of ``piw-master``. It also provides interactive functions
  for killing build slaves, and pausing / resuming / killing the master process
  itself.
"""

# Stop pylint's crusade against nicely aligned code
# pylint: disable=bad-whitespace
# flake8: noqa

__project__      = 'piwheels'
__version__      = '0.9'
__keywords__     = ['raspberrypi', 'pip', 'wheels']
__author__       = 'Ben Nuttall'
__author_email__ = 'ben@raspberrypi.org'
__url__          = 'https://www.piwheels.hostedpi.com/'
__platforms__    = 'ALL'

__requires__ = ['configargparse', 'pyzmq']

__extra_requires__ = {
    'monitor': ['urwid'],
    'master':  ['sqlalchemy', 'psycopg2'],
    'slave':   ['pip', 'wheel', 'python-dateutil'],
    'test':    ['pytest', 'coverage'],
    'doc':     ['sphinx'],
}

__classifiers__ = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 3',
]

__entry_points__ = {
    'console_scripts': [
        'piw-master = piwheels.master:main',
        'piw-slave = piwheels.slave:main',
        'piw-monitor = piwheels.monitor:main',
        'piw-initdb = piwheels.initdb:main',
        'piw-import = piwheels.importer:main',
    ],
}
