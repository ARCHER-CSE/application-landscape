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
import numpy as np
import progressbar as pb

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
    appUseT = pt.PrettyTable(['App', 'Users', 'Jobs', '% Jobs', 'Usage / kAU', '% Usage'])
    appStatT = pt.PrettyTable(['App', 'Min', 'Q1', 'Median', 'Q3', 'Max', 'Mean Size by Use'])
    appP = pb.ProgressBar(maxval=nApp)
    i = 0
    appP.start()
    for app in appA:
        appRegexp = app.regexp
        # Create the view for this app
        appV = xq.createRunView(xaltC, "exec_path", appRegexp)
        appUsers = xq.getAppUsers(xaltC, appV)
        appDataA = xq.getAppData(xaltC, appV)
        if appUsers > 0:
            appSumA = np.sum(appDataA, axis=0)
            appMinA = np.min(appDataA, axis=0)
            appMaxA = np.max(appDataA, axis=0)

            appTotJob = appSumA[2]
            appTotUse = appSumA[3]
            appTotWeight = appSumA[4]

            useSum = 0.0
            quartiles = [ 0, 0, 0 ]
            qval = [appTotUse*0.25, appTotUse*0.5, appTotUse*0.75]
            for rowA in appDataA:
                useSum += rowA[3]
                nodes = rowA[0]
                if qval[0] >= useSum: quartiles[0] = nodes
                if qval[1] >= useSum: quartiles[1] = nodes
                if qval[2] >= useSum: quartiles[2] = nodes

            meanByUse = appTotWeight/appTotUse
            
            pJob = 100.0 * appSumA[2]/totjobs
            pUse = 100.0 * appSumA[3]/totkau
            appUseT.add_row([app.name, appUsers, appSumA[2], pJob, appSumA[3], pUse])
            appStatT.add_row([app.name, appMinA[0]] + quartiles + [appMaxA[0], meanByUse])
        xq.dropView(xaltC, appV)
        appP.update(i)
        i += 1
    appP.finish()

    appUseT.sortby = 'Usage / kAU'
    appUseT.reversesort = True
    appUseT.align = "r"
    appUseT.align["App"] = "c"
    appUseT.float_format['Jobs'] = '.0'
    appUseT.float_format['% Jobs'] = '.2'
    appUseT.float_format['Usage / kAU'] = '.3'
    appUseT.float_format['% Usage'] = '.2'
    print '\n', appUseT, '\n'

    appStatT.align = "r"
    appStatT.align["App"] = "c"
    appStatT.float_format['Min'] = '.0'
    appStatT.float_format['Max'] = '.0'
    appStatT.float_format['Mean Size by Job'] = '.2'
    appStatT.float_format['Mean Size by Use'] = '.2'
    print '\n', appStatT, '\n'


    if useView:
       xq.dropView(xaltC, xaltRunT)
    
    # Close the database and exit nicely
    xaltDB.close()
    sys.exit(0)

          
if __name__ == "__main__":
    main(sys.argv[1:])

