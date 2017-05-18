#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2012
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
#******************************************************************************
#
# "@(#) $Id: ngamsDbSnapShotTest.py,v 1.4 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  21/11/2003  Created
#
"""
This module contains the Test Suite for the DB Snapshot Feature.
"""

import commands
import glob
import os
import sys
import time

from ngamsLib.ngamsCore import NGAMS_CLONE_CMD, NGAMS_REMFILE_CMD, \
    NGAMS_REMDISK_CMD, checkCreatePath, NGAMS_REGISTER_CMD
from ngamsTestLib import saveInFile, ngamsTestSuite, runTest, sendPclCmd


NM2IDX = "___NM2ID___"
IDX2NM = "___ID2NM___"


def _parseDbSnapshot(dbSnapshotDump):
    """
    Convert the contents of the DB Snapshot into a format that can be
    used as basis for comparing the test output.

    dbSnapshotDump:   Raw DB Snapshot dump as generated by
                      ngasUtils.ngasDumpDbSnapshot (string).

    Returns:          Converted DB Snapshot (string).
    """
    lines = dbSnapshotDump.split("\n")
    mapDic = {}
    fileDic = {}
    for line in lines:
        if (line.strip() == ""): continue
        if ((line.find(NM2IDX) != -1) or (line.find(IDX2NM) != -1)):
            key, val = line.split(" = ")
            mapDic[key] = val
        elif ((line.find("___MAP_COUNT___") == -1) and
              (line.find("Dumping") == -1)):
            key, val = line.split(" = ")
            fileDic[key] = eval(val)
    convDbSnapshot = "CONVERTED DB SNAPSHOT:\n"
    fileDicKeys = fileDic.keys()
    fileDicKeys.sort()
    for file in fileDicKeys:
        convDbSnapshot += "\nFILE: " + file + "\n"
        fileInfo = fileDic[file]
        fileInfoKeys = fileInfo.keys()
        fileInfoKeys.sort()
        for key in fileInfoKeys:
            val = fileInfo[key]
            col = mapDic[IDX2NM + str(key)]
            if ((col.find("ingestion_date") == -1) and
                (col.find("creation_date") == -1) and
                (col.find("io_time") == -1)):
                convDbSnapshot += "%-16s = %s\n" % (col, val)
    return convDbSnapshot


def _checkContDbSnapshot(testSuiteObj,
                         testCaseNo,
                         dataDirList,
                         waitEmptyCache = True,
                         filterContents = True):
    """
    Function to check the contents of a DB Snapshot file.

    testSuiteObj:   Reference to Test Suite Object (ngamsTestSuite).

    testCaseNo:     Test Case number (integer).

    dataDirList:    List of directories under the NGAS Root Mount Point
                    to check (list).

    Returns:        Void.
    """
    dirPat = "/tmp/ngamsTest/NGAS/%s/.db/NgasFiles.bsddb"
    cacheDirPat = "/tmp/ngamsTest/NGAS/%s/.db/cache"
    refFilePat = "ref/ngamsDbSnapShotTest_test_DbSnapshot_%d_%d.ref"
    count = 1
    startTime = time.time()
    for dataDir in dataDirList:
        # Wait till the DB Snapshot Cache Dir is empty.
        if (waitEmptyCache):
            cacheDir = cacheDirPat % dataDir
            startTime = time.time()
            while (((time.time() - startTime) < 10) and
                   (not os.path.exists(cacheDir))):
                time.sleep(0.200)
            startTime = time.time()
            while ((time.time() - startTime) < 20):
                tmpDbSnapshot = glob.glob(cacheDir + "/*")
                if (len(tmpDbSnapshot) == 0): break
                time.sleep(0.200)

        complName = dirPat % dataDir
        refFile = refFilePat % (testCaseNo, count)
        tmpFile = complName + ".dump"
        while ((not os.path.exists(complName)) and
               ((time.time() - startTime) < 10)):
            time.sleep(0.200)
        testSuiteObj.checkEqual(1, os.path.exists(complName),
                                "DB Snapshot missing: " + complName)
        cmd = "ngamsDumpDbSnapshot " + complName
        out = commands.getstatusoutput(cmd)[1]
        if (filterContents):
            snapshotDump = _parseDbSnapshot(out)
        else:
            snapshotDump = out
        saveInFile(tmpFile, snapshotDump)
        testSuiteObj.checkFilesEq(refFile, tmpFile,
                                  "Incorrect contents of DB Snapshot")
        count += 1


def _prepSrv(testSuiteObj):
    """
    Prepare a server instance for these tests.

    testSuiteObj:    Instance of the NG/AMS Test Suite object (ngamsTestSuite)

    Returns:         Instance of NG/AMS Cfg. and DB Objects
                     (tuple/ngamsConfig,ngamsDb).
    """
    return testSuiteObj.prepExtSrv(cfgProps=[["NgamsCfg.JanitorThread[1].SuspensionTime", "0T00:00:01"]])


class ngamsDbSnapShotTest(ngamsTestSuite):
    """
    Synopsis:
    Test DB Snapshot Feature.

    Description:
    The purpose of the Test Suite is to test the DB Snapshot Feature, which
    purpose it is to synchronize the various, remotely located NGAS DBs.

    In particular the following Use Cases are considered:

    =========================================================================
    | DB | Snapshot | Disk | Reaction                                       |
    -------------------------------------------------------------------------
    | +  |    +     |  +   | No changes.                                    |
    -------------------------------------------------------------------------
    | +  |    -     |  +   | Snapshot updated.                              |
    -------------------------------------------------------------------------
    | +  |    +     |  -   | 'Lost File' - Email Notification.              |
    -------------------------------------------------------------------------
    | -  |    +     |  +   | DB updated according to DB Snapshot.           |
    -------------------------------------------------------------------------
    | -  |    -     |  +   | TBI.                                           |
    -------------------------------------------------------------------------
    | -  |    -     |  -   | Irrelevant.                                    |
    =========================================================================

    Missing Test Cases:
    Should be reviewed carefully and the possibly, missing Test Cases added.

    - Creation of DB Snapshot at server start-up, files on the disk.
    """

    def test_DbSnapshot_1(self):
        """
        Synopsis:
        Creation of DB Snapshot at server start-up.

        Description:
        Test that DB Snapshot is created when a disk is initialized. This both
        for an empty DB and a DB with files registered where files are located
        on the disk.

        Expected Result:
        When the server goes Online and the Janitor Thread is launched the
        first time, it should detect that there is no DB Snapshot on the
        disk and therefore created it. In this case it will be empty as
        there are no files on the disk.

        Test Steps:
        - Prepare an instance of the NG/AMS Server and wait till the
          Janitor Thread has executed once.
        - Check that the DB Snapshot file for the disk in Slot 1 has been
          created.

        Remarks:
        ...
        """
        cfgObj, dbObj = _prepSrv(self)
        _checkContDbSnapshot(self, 1,
                             ["FitsStorage1-Main-1", "PafStorage-Rep-8"],
                             waitEmptyCache=False, filterContents=False)


    def test_DbSnapshot_2(self):
        """
        Synopsis:
        Test that DB Snapshot is updated when files are archived.

        Description:
        The purpose of this test is to verify that the DB Snapshot is updated
        'real-time' when files are archived onto a disk.

        Expected Result:
        After having archived 3 files, the Janitor Thread should be
        triggered to update the DB Snapshot.

        Test Steps:
        - Prepare instance of NG/AMS Server.
        - Archive a small FITS file 3 times.
        - Wait till the Temporary File Snapshots have been handled by
          the Janitor Thread.
        - Check that the DB Snapshot has been updated accordingly.

        Remarks:
        ...

        """
        cfgObj, dbObj = _prepSrv(self)
        client = sendPclCmd()
        for n in range(3): client.archive("src/SmallFile.fits")
        _checkContDbSnapshot(self, 2, ["FitsStorage1-Main-1",
                                       "FitsStorage1-Rep-2"])


    def test_DbSnapshot_3(self):
        """
        Synopsis:
        Test that DB Snapshot is updated correctly when files are removed.

        Description:
        The purpose of this test is to verify that the DB Snapshot is updated
        'real-time' when files are removed from a disk.

        Expected Result:
        After having executed the REMDFILE command on one of the files stored
        on the disk, the DB Snapshot should be updated by the Janitor Thread.

        Test Steps:
        - Prepare instance of NG/AMS Server.
        - Archive a small FITS file 3 times.
        - Issue a REMFILE Command to remove one of the files.
        - Wait till the Temporary File Snapshots have been handled by
          the Janitor Thread.
        - Check that the DB Snapshot has been updated accordingly.

        Remarks:
        ...
        """
        cfgObj, dbObj = _prepSrv(self)
        client = sendPclCmd()
        for n in range(3): client.archive("src/SmallFile.fits")
        diskId = "tmp-ngamsTest-NGAS-FitsStorage1-Main-1"
        client.get_status(NGAMS_CLONE_CMD, pars = [["disk_id", diskId]])
        fileId = "TEST.2001-05-08T15:25:00.123"
        client.get_status(NGAMS_REMFILE_CMD,
                          pars = [["disk_id", diskId],
                                  ["file_id", fileId],
                                  ["file_version", "2"],
                                  ["execute", "1"]])
        _checkContDbSnapshot(self, 3, ["FitsStorage1-Main-1"])


    def test_DbSnapshot_4(self):
        """
        Synopsis:
        DB Snapshot is updated correctly when a disk is removed (REMDISK'ed).

        Description:
        The purpose of this test is to verify that the DB Snapshot of a disk
        is correctly updated when the files contained and registered on the
        disks are removed via a REMDISK Command.

        Expected Result:
        A while after executing the REMDISK Command, the corresponding entries
        should disappear from the DB Snapshot of the REMDISK'ed disk.

        Test Steps:
        - Start a server.
        - Archive a small FITS file 3 times.
        - Clone the disk.
        - Remove the resulting, cloned disk.
        - Check that within a short time-out, all entries from the DB
          Snapshot disappears.

        Remarks:
        ...
        """
        cfgObj, dbObj = _prepSrv(self)
        client = sendPclCmd()
        for n in range(3): client.archive("src/SmallFile.fits")
        diskId = "tmp-ngamsTest-NGAS-FitsStorage1-Main-1"
        client.get_status(NGAMS_CLONE_CMD, pars = [["disk_id", diskId]])
        client.get_status(NGAMS_REMDISK_CMD, pars = [["disk_id", diskId], ["execute", "1"]])
        time.sleep(1)
        _checkContDbSnapshot(self, 4, ["FitsStorage1-Main-1"])


    def test_DbSnapshot_5(self):
        """
        Synopsis:
        Test that DB Snapshot is updated correctly when files are cloned.

        Description:
        The purpose of the test is to verify that the DB Snapshot on a disk,
        is updated (on-the-fly) when files are being cloned onto it.

        Expected Result:
        A short time after the files have been cloned onto a given disk,
        the information about the files should appear in the DB Snapshot
        of the disk.

        Test Steps:
        - Start server.
        - Archive a small test FITS file 3 times.
        - Clone the Main Disk hosting the 3 files archived.
        - Check that the DB Snapshot of the Target Disk has been updated with
          the information about the files cloned.

        Remarks:
        ...
        """
        cfgObj, dbObj = _prepSrv(self)
        client = sendPclCmd()
        for n in range(3): client.archive("src/SmallFile.fits")
        diskId = "tmp-ngamsTest-NGAS-FitsStorage1-Main-1"
        client.get_status(NGAMS_CLONE_CMD, pars = [["disk_id", diskId]])
        time.sleep(5)
        _checkContDbSnapshot(self, 5, ["FitsStorage2-Main-3"])


    def test_DbSnapshot_6(self):
        """
        Synopsis:
        Test that DB Snapshot is updated correctly when file are registered.

        Description:
        The purpose of the test is to verify that the DB Snapshot of a disk
        on which files are being registered, is properly updated according
        to the files registered.

        Expected Result:
        After a short while, the information for the files registered should
        appear in the DB Snapshot of the disk.

        Test Steps:
        - Start server.
        - Copy over a small test FITS file in 3 copies.
        - Send a REGISTER Command to register the files copied over
          (specifying root directory of the files).
        - Check that the DB Snapshot is updated within a given period of time.

        Remarks:
        ...
        """
        cfgObj, dbObj = _prepSrv(self)
        client = sendPclCmd()
        regTestDir = "/tmp/ngamsTest/NGAS/FitsStorage1-Main-1/reg_test"
        checkCreatePath(regTestDir)
        for n in range(3):
            os.system("cp src/SmallFile.fits " + regTestDir +\
                      "/" + str(n) + ".fits")
        client.get_status(NGAMS_REGISTER_CMD, pars = [["path", regTestDir]])
        _checkContDbSnapshot(self, 6, ["FitsStorage1-Main-1"], 1, 1)


    def test_DbSnapshot_7(self):
        """
        Synopsis:
        Test that DB is updated correctly according to DB Snapshot.

        Description:
        The purpose of the test is to verify that the DB is updated according
        to the information in the DB Snapshot. This goes both for adding
        missing entries and removing entries no longer stored on the disk and
        registered in the DB Snapshot.

        Expected Result:
        After bringing the NG/AMS Server Online, the Janitor Thread should
        update the DB according to the DB Snapshot.

        Test Steps:
        - Start an NG/AMS Server.
        - Archive a file 3 times.
        - Bring the server Offline.
        - Delete the info for the previously archived from the NGAS DB.
        - Bring the server Online.
        - Verify that the entries in the DB Snapshot now appear in the
          NAGS DB.

        Remarks:
        TODO!: Last step of verifying that the file info is actually updated
               in the DB, is not yet implemented.
        """
        cfgObj, dbObj = _prepSrv(self)
        client = sendPclCmd()
        for n in range(3): client.archive("src/SmallFile.fits")

        # Bring server Offline.
        client.offline()

        # Remove the file entries from the DB.
        dbObj.query2("DELETE FROM ngas_files")

        # Bring server Online.
        client.online()

        # TODO: Check that the file entries are now in the DB.


def run():
    """
    Run the complete test.

    Returns:   Void.
    """
    runTest(["ngamsDbSnapShotTest"])


if __name__ == '__main__':
    """
    Main program executing the test cases of the module test.
    """
    runTest(sys.argv)


# EOF
