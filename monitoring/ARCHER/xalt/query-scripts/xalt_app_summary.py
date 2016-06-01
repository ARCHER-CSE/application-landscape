#!/usr/bin/env python
#
# Generate useful statistics from the XALT database
#
import MySQLdb
import sys
import getopt
import prettytable as pt
import os
import fnmatch

import XALTQuery as xq

from code_def import CodeDef

def main(argv):

    #=======================================================
    # Read any code definitions
    #=======================================================
    appConfigDir = '/disk/archer-logs0/home/aturner/application-landscape/monitoring/ARCHER/xalt/descriptions'
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
    # Read the command-line options
    try:
        opts, args = getopt.getopt(argv, "p:c:h", 
                 ["project=", "config=", "help"])
    except getopt.GetoptError:
        error.handleError("Could not parse command line options\n")

    project = None
    app = None
    configFile = None
    for opt, arg in opts:
       if opt in ('-p', '--project'):
           project = arg.strip()
       elif opt in ('-c', '--config'):
           configFile = arg.strip()

    if app is not None and project is not None:
       print "Error: cannot specify both project and application at the same time."
       sys.exit(1)

    dbConfigF = open(configFile, "r")
    host, user, passwd, dbname, sockloc = dbConfigF.readline().split()
    dbConfigF.close()

    xaltDB = MySQLdb.connect(host, user, passwd, dbname, unix_socket=sockloc)
    xaltC = xaltDB.cursor()

    xaltRunT = 'xalt_run'
    useView = False
    if project is not None:
        xaltRunT = xq.createRunView(xaltC, 'account', project) 
        print 'Hybrid jobs usage for project: {0}'.format(project)
        useView = True
    elif app is not None:
        xaltRunT = xq.createRunView(xaltC, 'exec_path', app)
        useView = True
     
    # Get total data
    totjobs, totkau = xq.getTotUse(xaltC, xaltRunT)
    print '\nTotal usage and jobs:\n\tJobs = {:d}\n\t kAU = {:.3f}'.format(totjobs, totkau)

    # Loop over codes getting total usage
    for app in appA:
        appRegexp = app.regexp
        jobs, usage = xq.getAppTotal(xaltC, xaltRunT, appRegexp)
        print app.name, jobs, usage

    if useView:
       xq.dropView(xaltC, xaltRunT)
    
    # Close the database and exit nicely
    xaltDB.close()
    sys.exit(0)

          
if __name__ == "__main__":
    main(sys.argv[1:])

