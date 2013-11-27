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
# "@(#) $Id: ngamsNgLogPlugIn.py,v 1.2 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  09/07/2001  Created
#

"""
This Data Archiving Plug-In is used to handle reception and processing
of NG/AMS (OLAS Style) log files.

Note, that the plug-in is implemented for the usage at ESO. If used in other
contexts, a dedicated plug-in matching the individual context should be
implemented and NG/AMS configured to use it.
"""

import os, multifile, string
from   ngams import *
import ngamsPlugInApi, ngamsDiskUtils, ngamsDiskInfo


def ngamsNgLogPlugIn(srvObj,
                     reqPropsObj):
    """
    Data Archiving Plug-In to handle archiving of NG/AMS (OLAS style) log
    files.

    srvObj:       Reference to NG/AMS Server Object (ngamsServer).

    reqPropsObj:  NG/AMS request properties object (ngamsReqProps).

    Returns:      Standard NG/AMS Data Archiving Plug-In Status
                  as generated by: ngamsPlugInApi.genDapiSuccessStat()
                  (ngamsDapiStatus).
    """
    # For now the exception handling is pretty basic:
    # If something goes wrong during the handling it is tried to
    # move the temporary file to the Bad Files Area of the disk.
    info(1,"Plug-In handling data for file: " +
         os.path.basename(reqPropsObj.getFileUri()))
    diskInfo = reqPropsObj.getTargDiskInfo()
    stagingFilename = reqPropsObj.getStagingFilename()
    ext = os.path.splitext(stagingFilename)[1][1:]

    # Now, build final filename. We do that by taking the date of
    # the first log entry.
    #
    #    2001-07-09T14:37:59.563 [INFO] Logging properties defined ...
    #
    # Alternatively the first entry could be of the form, e.g.:
    #
    #    2003-12-29T09:21:57.608 [INFO] LOG-ROTATE: 1072689717 - \
    #      SYSTEM-ID: ngamsArchiveClient@ngasdev2
    #
    # In the former case the Log ID is equal to the NGAS ID. In the latter
    # case, the Log ID is equal to the System ID.
    #
    # The final filename is built as follows: <Log ID>.<date>.<ext>
    #
    # The file_id is: <Log ID>.<date>
    fo = open(stagingFilename, "r")
    firstLine = fo.readline()
    fo.close()
    try:
        # Compress the log file.
        uncomprSize = ngamsPlugInApi.getFileSize(stagingFilename)
        compression = "gzip"
        info(2,"Compressing file using: %s ..." % compression)
        exitCode, stdOut = ngamsPlugInApi.execCmd("%s %s" %\
                                                  (compression,
                                                   stagingFilename))
        if (exitCode != 0):
            errMsg = "ngamsNgLogPlugIn: Problems during archiving! " +\
                     "Compressing the file failed"
            raise Exception, errMsg
        stagingFilename = stagingFilename + ".nglog.gz"
        # Remember to update the Temporary Filename in the Request
        # Properties Object.
        reqPropsObj.setStagingFilename(stagingFilename)
        info(2,"Log file compressed")

        # Parse first line of the log file.
        timeStamp = firstLine.split(" ")[0]
        date = timeStamp.split("T")[0]
        sysIdIdx = firstLine.find("SYSTEM-ID")
        if (sysIdIdx != -1):
            logId = firstLine[sysIdIdx + len("SYSTEM-ID:"):].strip().\
                    split(" ")[0]
        else:
            logId = ngamsPlugInApi.genNgasId(srvObj.getCfg())
        fileId = logId + "." + timeStamp
        fileVersion, relPath, relFilename,\
                     complFilename, fileExists =\
                     ngamsPlugInApi.genFileInfo(srvObj.getDb(),
                                                srvObj.getCfg(),
                                                reqPropsObj, diskInfo,
                                                stagingFilename, fileId,
                                                fileId, [date])

        # Generate status.
        info(4,"Generating status ...")
        format = ngamsPlugInApi.determineMimeType(srvObj.getCfg(),
                                                  stagingFilename)
        fileSize = ngamsPlugInApi.getFileSize(stagingFilename)
        return ngamsPlugInApi.genDapiSuccessStat(diskInfo.getDiskId(),
                                                 relFilename,
                                                 fileId, fileVersion, format,
                                                 fileSize, uncomprSize,
                                                 compression, relPath,
                                                 diskInfo.getSlotId(),
                                                 fileExists, complFilename)
    except Exception, e:
        raise Exception, "ngamsNgLogPlugIn: Error handling log file: " +\
              stagingFilename + ". Rejecting."


# EOF
