#!/usr/bin/env python
#
# Run through unidentified jobs and set the application
#
import MySQLdb
import sys
import getopt
import os
import fnmatch

import XALTQuery as xq

from code_def import CodeDef

def main(argv):

    #=======================================================
    # Read any code definitions
    #=======================================================
    appConfigDir = os.environ['XALT_APP_DESCRIPTIONS']
    appA = []
    nApp = 0
    # Create a dictionary of codes
    appD = {}
    for file in os.listdir(appConfigDir):
        if fnmatch.fnmatch(file, '*.code'):
            nApp += 1
            app = CodeDef()   
            app.readConfig(appConfigDir + '/' + file)
            appA.append(app)
            appD[app.name] = nApp - 1

    #=======================================================
    # Command line options
    #=======================================================
    try:
        opts, args = getopt.getopt(argv, "c:h", 
                 ["config=", "help"])
    except getopt.GetoptError:
        error.handleError("Could not parse command line options\n")

    project = None
    configFile = None
    for opt, arg in opts:
       if opt in ('-c', '--config'):
           configFile = arg.strip()

    #=======================================================
    # Setup the database connection
    #=======================================================
    dbConfigF = open(configFile, "r")
    host, user, passwd, dbname, sockloc = dbConfigF.readline().split()
    dbConfigF.close()

    xaltDB = MySQLdb.connect(host, user, passwd, dbname, unix_socket=sockloc)
    xaltC = xaltDB.cursor()

    #=======================================================
    # Loop over applications searching for unidentified jobs
    #=======================================================
    for app in appA:
        appName = app.name
        appRegexp = app.regexp
        xq.updateAppName(xaltC, appName, appRegexp)
    
    # Close the database and exit nicely
    xaltDB.close()
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])

