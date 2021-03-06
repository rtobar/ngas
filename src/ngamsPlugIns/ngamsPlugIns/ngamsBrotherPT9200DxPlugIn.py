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
# "@(#) $Id: ngamsBrotherPT9200DxPlugIn.py,v 1.4 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# awicenec/
# jknudstr  10/05/2001  Created
#
"""
This module contains a plug-in driver for printing labels on
the Brother PT-9200DX label printer.
"""
# TODO: Build in a semaphore protection to avoid that more than one
#       request is executed simultaneously attempting to print a label.
#       Parallel access to the label printer may harm the printer.
#       The entire code of the Label Printer Plug-In
#       (ngamsBrotherPT9200DxPlugIn) should be semaphore protected and
#       before exiting the function, a sleep of ~5s should be done. After
#       that the semaphore can be released. If another requests tries to
#       enter the semaphore protected region while one request is being
#       executed, an exception will be raised.
#       Implementing this, the _labelPrinterSem semaphore can be removed
#       from the ngamsLabelCmd.py module.

import logging
import os
import sys

from ngamsLib import ngamsPlugInApi, ngamsConfig
from ngamsLib.ngamsCore import NGAMS_NOTIF_ERROR


logger = logging.getLogger(__name__)

def genFontsDictionary(fnm):

    """
    Function reads the contents of a bitmap character file <fnm>.
    The character contents of this file has to be compliant with the  keys:

    keys = ['Header','-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            ':', 'A','B','C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
            'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
            'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
            'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
            'z', 'Trailer']

    These keys are used to fill a dictionary with the bitmaps and can
    then be used to print strings on the Brother pTouch 9200DX
    printer.

    Synopsis:  charDict = ngamsGetCharDict(<fnm>)

    fnm:        Filename of font definition file (string).

    Returns:    Return value is a dictionary with the keys
                given above (dictionary).
    """
    keys = ['Header','-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            ':', 'A','B','C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
            'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
            'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
            'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
            'z', 'Trailer']

    try:
        f = open(fnm)
        charArr = f.read()
        f.close()
    except Exception, e:
        errMsg = "Problems opening CharDict file"
        logger.error(errMsg)
        raise

    charArr = charArr.split('ZG')
    charDict = {}
    i = 0
    if len(charArr) != len(keys):
        errMsg = 'Wrong number of characters in CharDict file: ' + fnm
        logger.error(errMsg)
        raise Exception(errMsg)

    for k in keys:
        if k == 'Header' or k == 'Trailer':
            charDict.update({k:charArr[i]})
        else:
            charDict.update({k:'G'+charArr[i]})   # put the G back
        charDict.update({' ':'ZZZZZZZZZZZZZ'})    # add a blank
        i = i + 1

    return charDict


def ngamsBrotherPT9200DxPlugIn(srvObj,
                               label,
                               reqPropsObj = None):
    """
    Driver for printing labels on the label printer Brother PT-9200DX.

    srvObj:           Reference to instance of the NG/AMS Server
                      class (ngamsServer).

    label:            Label text to print (string).

    reqPropsObj:      NG/AMS request properties object (ngamsReqProps).

    Returns:          Void.
    """
    plugInPars = srvObj.getCfg().getLabelPrinterPlugInPars()
    logger.info("Executing plug-in ngamsBrotherPT9200DxPlugIn with parameters: " + \
                "%s - Label: %s ...", plugInPars, label)
    parDic = ngamsPlugInApi.parseRawPlugInPars(plugInPars)

    # Get the font bit pattern dictionary.
    fontDic = genFontsDictionary(parDic["font_file"])

    # Generate the printer control code.
    printerCode = fontDic["Header"]
    for i in range(len(label)):
        if (not fontDic.has_key(label[i])):
            errMsg = "No font defintion for character: \"" + label[i] +\
                     "\" - in font definition file: " + parDic["font_file"] +\
                     " - cannot generate disk label: " + label
            ngamsPlugInApi.notify(srvObj, NGAMS_NOTIF_ERROR,
                                  "ngamsBrotherPT9200DxPlugIn: " +\
                                  "ILLEGAL CHARACTER REQ. FOR PRINTING",
                                  errMsg)
            raise Exception(errMsg)

        printerCode = printerCode + fontDic[label[i]]
    printerCode = printerCode + fontDic["Trailer"]

    # Generate printer file, write the printer control code.
    tmpDir = ngamsPlugInApi.getTmpDir(srvObj.getCfg())
    ngasId = srvObj.getHostId()
    printerFilename = os.path.normpath(tmpDir + "/ngamsLabel_" + ngasId+".prn")
    fo = open(printerFilename, "w")
    fo.write(printerCode)
    fo.close()

    # Write the printer code file to the device.
    stat, out = ngamsPlugInApi.execCmd("cat " + printerFilename + " > " +\
                                       parDic["dev"])

    # This was previously excluded during the "test mode"; a proper way is by
    # having a configurable parameter
    print parDic
    if not 'keep_printer_file' in parDic:
        os.system("rm -f " + printerFilename)

    if (stat != 0):
        errMsg = "Problem occurred printing label! Error: " + str(out)
        ngamsPlugInApi.notify(srvObj, NGAMS_NOTIF_ERROR,
                              "ngamsBrotherPT9200DxPlugIn: " +\
                              "PROBLEM PRINTING LABEL", errMsg)
        raise Exception(errMsg)


if __name__ == '__main__':
    """
    Main function.
    """
    if (len(sys.argv) != 3):
        print "\nCorrect usage is:\n"
        print "% (python) ngamsBrotherPT9200DxPlugIn <NGAMS CFG> <text>\n"
        sys.exit(1)
    cfg = ngamsConfig.ngamsConfig()
    cfg.load(sys.argv[1])
    ngamsBrotherPT9200DxPlugIn(cfg, sys.argv[2])


# EOF
