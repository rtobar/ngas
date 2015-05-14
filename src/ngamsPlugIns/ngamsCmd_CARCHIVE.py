#
#    ALMA - Atacama Large Millimiter Array
#    (c) European Southern Observatory, 2002
#    Copyright by ESO (in the framework of the ALMA collaboration),
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
# "@(#) $Id: ngamsCmd_QARCHIVE.py,v 1.6 2009/12/07 16:36:40 awicenec Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  03/02/2009  Created
#

"""
NGAS Command Plug-In, implementing a Quick Archive Command.

This works in a similar way as the 'standard' ARCHIVE Command, but has been
simplified in a few ways:

  - No replication to a Replication Volume is carried out.
  - Target disks are selected randomly, disregarding the Streams/Storage Set
    mappings in the configuration. This means that 'volume load balancing' is
    provided.
  - Archive Proxy Mode is not supported.
  - No probing for storage availability is supported.
  - In general, less SQL queries are performed and the algorithm is more
    light-weight.
  - crc is computed from the incoming stream
  - ngas_files data is 'cloned' from the source file
"""

from ngams import *
import random
import binascii
#import pcc, PccUtTime
import ngamsLib, ngamsDbCore, ngamsFileInfo
import ngamsDiskInfo, ngamsHighLevelLib
import ngamsCacheControlThread
from ngamsMIMEMultipart import MIMEMultipartHandler, MIMEMultipartParser

GET_AVAIL_VOLS_QUERY = "SELECT %s FROM ngas_disks nd WHERE completed=0 AND " +\
                       "host_id='%s'"

class ArchivingHandler(MIMEMultipartHandler):

    def __init__(self, writeBlockSize):
        self._fileDataList = []
        self._writeBlockSize = writeBlockSize
        self._writeTime = 0
        self._crcTime = 0

    def startContainer(self, containerName):
        info(4, 'Receiving a container with container_name=' + containerName)
        self._containerName = containerName

    def endContainer(self):
        info(4, 'Finished receiving container')

    def startFile(self, filename):
        info(4, 'Opening new file ' + filename)
        self._fdOut = open(filename, 'w')
        self._filename = filename
        self._crc = 0

    def handleData(self, buf, moreExpected):
        # Write always in _writeBlockSize blocks
        while len(buf) > self._writeBlockSize:
            block = buf[:self._writeBlockSize]
            buf = buf[self._writeBlockSize:]
            self.writeAndCRC(block)

        # If the content of this file has finished
        # arriving write the last piece to the file;
        # otherwise return the remaining data so it's
        # considered during the next call
        if not moreExpected:
            self.writeAndCRC(buf)
        elif len(buf) > 0:
            return buf

        return None

    def writeAndCRC(self, data):
        t = time.time()
        self._fdOut.write(data)
        self._writeTime += (time.time() - t)

        t = time.time()
        self._crc = binascii.crc32(data, self._crc)
        self._crcTime += (time.time() - t)

    def endFile(self):
        info(4, 'Closing file ' + self._filename)
        self._fileDataList.append([self._filename, self._crc])
        self._fdOut.close()

    def getContainerName(self):
        return self._containerName

    def getFileDataList(self):
        return self._fileDataList

    def getCrcTime(self):
        return self._crcTime

    def getWritingTime(self):
        return self._writeTime

def getTargetVolume(srvObj):
    """
    Get a random target volume with availability.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    Returns:        Target volume object or None (ngamsDiskInfo | None).
    """
    T = TRACE()

    sqlQuery = GET_AVAIL_VOLS_QUERY % (ngamsDbCore.getNgasDisksCols(),
                                       getHostId())
    res = srvObj.getDb().query(sqlQuery, ignoreEmptyRes=0)
    if (res == [[]]):
        return None
    else:
        # Shuffle the results.
        random.shuffle(res[0])
        return ngamsDiskInfo.ngamsDiskInfo().unpackSqlResult(res[0][0])


def updateDiskInfo(srvObj,
                   resDapi):
    """
    Update the row for the volume hosting the new file.

    srvObj:    Reference to NG/AMS server class object (ngamsServer).

    resDapi:   Result returned from the DAPI (ngamsDapiStatus).

    Returns:   Void.
    """
    T = TRACE()

    sqlQuery = "UPDATE ngas_disks SET " +\
               "number_of_files=(number_of_files + 1), " +\
               "bytes_stored=(bytes_stored + %d) WHERE " +\
               "disk_id='%s'"
    sqlQuery = sqlQuery % (resDapi.getFileSize(), resDapi.getDiskId())
    srvObj.getDb().query(sqlQuery, ignoreEmptyRes=0)

def saveInStagingFile(ngamsCfgObj,
                      reqPropsObj,
                      stagingFilename,
                      diskInfoObj):
    """
    Save the data ready on the HTTP channel, into the given Staging
    Area file.

    ngamsCfgObj:     NG/AMS Configuration (ngamsConfig).

    reqPropsObj:     NG/AMS Request Properties object (ngamsReqProps).

    stagingFilename: Staging Area Filename as generated by
                     ngamsHighLevelLib.genStagingFilename() (string).

    diskInfoObj:     Disk info object. Only needed if mutual exclusion
                     is required for disk access (ngamsDiskInfo).

    Returns:         Void.
    """
    T = TRACE()

    try:
        blockSize = ngamsCfgObj.getBlockSize()
        return saveFromHttpToFile(ngamsCfgObj, reqPropsObj, stagingFilename,
                                  blockSize, 1, diskInfoObj)
    except Exception, e:
        errMsg = genLog("NGAMS_ER_PROB_STAGING_AREA", [stagingFilename,str(e)])
        error(errMsg)
        raise Exception, errMsg


def saveFromHttpToFile(ngamsCfgObj,
                       reqPropsObj,
                       trgFilename,
                       blockSize,
                       mutexDiskAccess = 1,
                       diskInfoObj = None):
    """
    Save the data available on an HTTP channel into the given file.

    ngamsCfgObj:     NG/AMS Configuration object (ngamsConfig).

    reqPropsObj:     NG/AMS Request Properties object (ngamsReqProps).

    trgFilename:     Target name for file where data will be
                     written (string).

    blockSize:       Block size (bytes) to apply when reading the data
                     from the HTTP channel (integer).

    mutexDiskAccess: Require mutual exclusion for disk access (integer).

    diskInfoObj:     Disk info object. Only needed if mutual exclusion
                     is required for disk access (ngamsDiskInfo).

    Returns:         Tuple. Element 0: Time in took to write
                     file (s) (tuple).
    """
    T = TRACE()
    CRLF = '\r\n'

    checkCreatePath(os.path.dirname(trgFilename))
##    fdOut = open(trgFilename, "w")
##    info(2,"Saving data in file: " + trgFilename + " ...")

    saveDir = trgFilename.rsplit('/', 1)[0] + '/'

    timer = PccUtTime.Timer()
    try:
        # Make mutual exclusion on disk access (if requested).
        if (mutexDiskAccess):
            ngamsHighLevelLib.acquireDiskResource(ngamsCfgObj, diskInfoObj.getSlotId())

        # Distinguish between Archive Pull and Push Request. By Archive
        # Pull we may simply read the file descriptor until it returns "".
        if (ngamsLib.isArchivePull(reqPropsObj.getFileUri()) and
            not reqPropsObj.getFileUri().startswith('http://')):
            # (reqPropsObj.getSize() == -1)):
            # Just specify something huge.
            info(3,"It is an Archive Pull Request/data with unknown size")
            remSize = int(1e11)
        elif reqPropsObj.getFileUri().startswith('http://'):
            info(3,"It is an HTTP Archive Pull Request: trying to get Content-length")
            httpInfo = reqPropsObj.getReadFd().info()
            headers = httpInfo.headers
            hdrsDict = ngamsLib.httpMsgObj2Dic(''.join(headers))
            if hdrsDict.has_key('content-length'):
                remSize = int(hdrsDict['content-length'])
            else:
                info(3,"No HTTP header parameter Content-length!")
                info(3,"Header keys: %s" % hdrsDict.keys())
                remSize = int(1e11)
        else:
            remSize = reqPropsObj.getSize()
            info(3,"Archive Push/Pull Request - Data size: %d" % remSize)

        fd = reqPropsObj.getReadFd()
        handler = ArchivingHandler(blockSize)
        parser = MIMEMultipartParser(handler, fd, remSize, blockSize)
        parser.parse()
        deltaTime = timer.stop()


        containerName = handler.getContainerName()
        fileDataList  = handler.getFileDataList()
        crcTime       = handler.getCrcTime()
        writingTime   = handler.getWritingTime()
        readingTime   = parser.getReadingTime()
        bytesRead     = parser.getBytesRead()
        ingestRate    = (float(bytesRead) / deltaTime)
        reqPropsObj.setBytesReceived(bytesRead)

        info(4,"Transfer time: %.3f s; CRC time: %.3f s; write time %.3f s" % (readingTime, crcTime, writingTime))

        # Release disk resouce.
        if (mutexDiskAccess):
            ngamsHighLevelLib.releaseDiskResource(ngamsCfgObj, diskInfoObj.getSlotId())

        return [deltaTime,fileDataList,ingestRate, containerName]

    except Exception, e:
        #fdOut.close()
        # Release disk resouce.
        if (mutexDiskAccess):
            ngamsHighLevelLib.releaseDiskResource(ngamsCfgObj, diskInfoObj.getSlotId())
        raise Exception, e


def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle the Quick Archive (QARCHIVE) Command.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        (fileId, filePath) tuple.
    """
    T = TRACE()

##    # Check if the URI is correctly set.
##    info(3, "Check if the URI is correctly set.")
##    if (reqPropsObj.getFileUri() == ""):
##        errMsg = genLog("NGAMS_ER_MISSING_URI")
##        error(errMsg)
##        raise Exception, errMsg

    # Is this NG/AMS permitted to handle Archive Requests?
    info(3, "Is this NG/AMS permitted to handle Archive Requests?")
    if (not srvObj.getCfg().getAllowArchiveReq()):
        errMsg = genLog("NGAMS_ER_ILL_REQ", ["Archive"])
        raise Exception, errMsg
    srvObj.checkSetState("Archive Request", [NGAMS_ONLINE_STATE],
                         [NGAMS_IDLE_SUBSTATE, NGAMS_BUSY_SUBSTATE],
                         NGAMS_ONLINE_STATE, NGAMS_BUSY_SUBSTATE,
                         updateDb=False)

    # Get mime-type (try to guess if not provided as an HTTP parameter).
    info(3, "Get mime-type (try to guess if not provided as an HTTP parameter).")
    if (reqPropsObj.getMimeType() == ""):
        mimeType = ngamsHighLevelLib.\
                   determineMimeType(srvObj.getCfg(), reqPropsObj.getFileUri())
        reqPropsObj.setMimeType(mimeType)
    else:
        mimeType = reqPropsObj.getMimeType()


    ## Set reference in request handle object to the read socket.
    info(3, "Set reference in request handle object to the read socket.")
    if reqPropsObj.getFileUri().startswith('http://'):
        fileUri = reqPropsObj.getFileUri()
        readFd = ngamsHighLevelLib.openCheckUri(fileUri)
        reqPropsObj.setReadFd(readFd)

    # Determine the target volume, ignoring the stream concept.
    info(3, "Determine the target volume, ignoring the stream concept.")
    targDiskInfo = getTargetVolume(srvObj)
    if (targDiskInfo == None):
        errMsg = "No disk volumes are available for ingesting any files."
        error(errMsg)
        raise Exception, errMsg
    reqPropsObj.setTargDiskInfo(targDiskInfo)

    # Generate staging filename.
    info(3, "Generate staging filename from URI: %s" % reqPropsObj.getFileUri())
    if (reqPropsObj.getFileUri().find("file_id=") >= 0):
        file_id = reqPropsObj.getFileUri().split("file_id=")[1]
        baseName = os.path.basename(file_id)
    else:
        baseName = os.path.basename(reqPropsObj.getFileUri())
    stgFilename = os.path.join("/", targDiskInfo.getMountPoint(),
                               NGAMS_STAGING_DIR,
                               genUniqueId() + "___" + baseName)
    info(3, "Staging filename is: %s" % stgFilename)
    reqPropsObj.setStagingFilename(stgFilename)

    # Retrieve file contents (from URL, archive pull, or by storing the body
    # of the HTTP request, archive push).
    stagingInfo = saveInStagingFile(srvObj.getCfg(), reqPropsObj,
                                    stgFilename, targDiskInfo)
    ioTime = stagingInfo[0]
    reqPropsObj.incIoTime(ioTime)

    import ngamsPlugInApi
    import ngamsGenDapi
    import uuid

    parDic = {}
    ngamsGenDapi.handlePars(reqPropsObj, parDic)
    diskInfo = reqPropsObj.getTargDiskInfo()
    # Generate file information.
    info(3,"Generate file information")
    dateDir = PccUtTime.TimeStamp().getTimeStamp().split("T")[0]
    resDapiList = []

    containerId = uuid.uuid4()
    containerName = stagingInfo[3]
    containerSize = 0


    for item in stagingInfo[1]:
        filepath = item[0]
        crc = item[1]

        parDic['file_id'] = filepath

        fileVersion, relPath, relFilename,\
                     complFilename, fileExists =\
                     ngamsPlugInApi.genFileInfo(srvObj.getDb(),
                                                srvObj.getCfg(),
                                                reqPropsObj, diskInfo,
                                                filepath,
                                                filepath,
                                                filepath, [dateDir])
        complFilename, relFilename = ngamsGenDapi.checkForDblExt(complFilename,
                                                    relFilename)

##        # Compress the file if requested.
##        uncomprSize, archFileSize, format, compression, comprExt =\
##                     ngamsGenDapi.compressFile(srvObj, reqPropsObj, parDic)
        uncomprSize = ngamsPlugInApi.getFileSize(filepath)
        containerSize += uncomprSize
        comprExt = ""
        format = reqPropsObj.getMimeType()
        compression = "NONE"
        archFileSize = ngamsPlugInApi.getFileSize(filepath)

        resDapi = ngamsPlugInApi.genDapiSuccessStat(diskInfo.getDiskId(),
                                                     relFilename,
                                                     parDic['file_id'],
                                                     fileVersion, format,
                                                     archFileSize, uncomprSize,
                                                     compression, relPath,
                                                     diskInfo.getSlotId(),
                                                     fileExists, complFilename)
        # Move file to final destination.
        info(3, "Moving file to final destination")
        ioTime = mvFile(filepath,
                        resDapi.getCompleteFilename())
        reqPropsObj.incIoTime(ioTime)


        # Get crc info
        checksumPlugIn = "StreamCrc32"
        checksum = str(crc)
        info(3, "Invoked Checksum Plug-In: " + checksumPlugIn +\
                " to handle file: " + resDapi.getCompleteFilename() +\
                ". Result: " + checksum)

        # Get source file version
        # e.g.: http://ngas03.hq.eso.org:7778/RETRIEVE?file_version=1&file_id=X90/X962a4/X1
        info(3, "Get file version")
        file_version = resDapi.getFileVersion()
        if reqPropsObj.getFileUri().count("file_version"):
            file_version = int((reqPropsObj.getFileUri().split("file_version=")[1]).split("&")[0])

        # Check/generate remaining file info + update in DB.
        info(3, "Creating db entry")
        ts = PccUtTime.TimeStamp().getTimeStamp()
        creDate = getFileCreationTime(resDapi.getCompleteFilename())
        ignore = 0
        creDate = timeRef2Iso8601(creDate)
        sqlQuery = "INSERT INTO ngas_files " +\
                           "(disk_id, file_name, file_id, file_version, " +\
                           "format, file_size, " +\
                           "uncompressed_file_size, compression, " +\
                           "ingestion_date, file_ignore, checksum, " +\
                           "checksum_plugin, file_status, " +\
                           "creation_date, container_id) "+\
                           "VALUES " +\
                           "('" + resDapi.getDiskId() + "', " +\
                           "'" + resDapi.getRelFilename() + "', " +\
                           "'" + resDapi.getFileId() + "', " +\
                           "" + str(file_version) + ", " +\
                           "'" + resDapi.getFormat() + "', " +\
                           str(resDapi.getFileSize()) + ", " +\
                           str(resDapi.getUncomprSize()) + ", " +\
                           "'" + resDapi.getCompression() + "', " +\
                           "'" + ts + "', " +\
                           str(ignore) + ", " +\
                           "'" + checksum + "', " +\
                           "'" + checksumPlugIn + "', " +\
                           "'" + NGAMS_FILE_STATUS_OK + "', " +\
                           "'" + creDate + "', " +\
                           "'" + str(containerId) + "')"

        srvObj.getDb().query(sqlQuery)



        # Inform the caching service about the new file.
        info(3, "Inform the caching service about the new file.")
        if (srvObj.getCachingActive()):
            diskId      = resDapi.getDiskId()
            fileId      = resDapi.getFileId()
            fileVersion = file_version
            filename    = resDapi.getRelFilename()
            ngamsCacheControlThread.addEntryNewFilesDbm(srvObj, diskId, fileId,
                                                       fileVersion, filename)

        # Update disk info in NGAS Disks.
        info(3, "Update disk info in NGAS Disks.")
        updateDiskInfo(srvObj, resDapi)

        resDapiList.append(resDapi)

        sqlQuery = "INSERT INTO ngas_containers " +\
               "(container_id, container_name, ingestion_date, " +\
               "container_size, container_type) VALUES " +\
               "('" + str(containerId) + "', " +\
               "'" + containerName + "', " +\
               "'" + creDate + "', " +\
               str(containerSize) + ", " \
               "'logical'" +\
               ")"

    srvObj.getDb().query(sqlQuery)

    # Check if the disk is completed.
    # We use an approximate extimate for the remaning disk space to avoid
    # to read the DB.
    info(3, "Check available space in disk")
    availSpace = getDiskSpaceAvail(targDiskInfo.getMountPoint(), smart=False)
    if (availSpace < srvObj.getCfg().getFreeSpaceDiskChangeMb()):
        complDate = PccUtTime.TimeStamp().getTimeStamp()
        targDiskInfo.setCompleted(1).setCompletionDate(complDate)
        targDiskInfo.write(srvObj.getDb())

    # Request after-math ...
    srvObj.setSubState(NGAMS_IDLE_SUBSTATE)
    msg = "Successfully handled Archive Pull Request for data file " +\
          "with URI: " + reqPropsObj.getSafeFileUri()
    info(1, msg)
    srvObj.ingestReply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS,
                       NGAMS_SUCCESS, msg, targDiskInfo)


    for resDapi in resDapiList:
         # Trigger Subscription Thread. This is a special version for MWA, in which we simply swapped MIRRARCHIVE and QARCHIVE
         # chen.wu@icrar.org
        msg = "triggering SubscriptionThread for file %s" % resDapi.getFileId()
        info(3, msg)
        srvObj.addSubscriptionInfo([(resDapi.getFileId(),
                                     resDapi.getFileVersion())], [])
        srvObj.triggerSubscriptionThread()


    return (resDapi.getFileId(), '%s/%s' % (targDiskInfo.getMountPoint(), resDapi.getRelFilename()), stagingInfo[2])

# EOF

