#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2015
#    Copyright by UWA (in the framework of the ICRAR)
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#
import os

from setuptools import setup, find_packages

with open('../../VERSION') as vfile:
    for line in vfile.readlines():
        if "ngamsNGAMS_SW_VER" in line:
            version = line.split("NGAMS_SW_VER ")[1].strip()[1:-1]
            break

# We definitely require this one
install_requires = ['DBUtils']

# Users might opt out from depending on crc32c
# Our code is able to cope with that situation already
if 'NGAS_NO_CRC32C' not in os.environ:
    install_requires.append('crc32c')

# If there's neither bsddb nor bsddb3 we need to install the latter
try:
    import bsddb
except ImportError:
    try:
        import bsddb3
    except ImportError:
        # bsddb-6.2 doesn't support DB v6.0
        install_requires.append('bsddb3<6.2.0')

setup(
    name='ngamsCore',
    version=version,
    description="The base packages that make up the NGAMs system",
    long_description="The base modules that make up the NGAMs system, namely the ngamsLib, ngamsData and ngamsSql packages",
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='',
    author_email='',
    url='',
    license='',
    packages=find_packages(),
    include_package_data=True,
    package_data = {
        'ngamsSql' : ['*.sql'],
        'ngamsData': ['*.fnt', '*.xml', '*.dtd', 'COPYRIGHT', 'LICENSE', 'VERSION'],
        'ngamsLib' : ['README']
    },
    install_requires = install_requires
)
