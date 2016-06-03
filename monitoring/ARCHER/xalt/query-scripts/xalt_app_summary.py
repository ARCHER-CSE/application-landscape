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
import ReportUtil as ru

from code_def import CodeDef

def main(argv):

    #=======================================================
    # Configuration
    #=======================================================
    sizeBinsA = [1, 2, 3, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]
    timeBinsA = [1, 3, 6, 12, 24, 48]

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
    try:
        opts, args = getopt.getopt(argv, "p:c:h", 
                 ["project=", "config=", "help"])
    except getopt.GetoptError:
        error.handleError("Could not parse command line options\n")

    project = None
    configFile = None
    for opt, arg in opts:
       if opt in ('-p', '--project'):
           project = arg.strip()
       elif opt in ('-c', '--config'):
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
    # Run the report
    #=======================================================
    xaltRunT = 'xalt_run'
    useView = False
    if project is not None:
        xaltRunT = xq.createRunView(xaltC, 'account', project) 
        print '\nApplication Data for Project: {0}\n'.format(project)
        useView = True
    else:
        print '\nOverall Application Data\n'
     
    # Get total data
    totjobs, totkau = xq.getTotUse(xaltC, xaltRunT)
    print '\nTotal usage and jobs:\n\tJobs = {:d}\n\t kAU = {:.3f}'.format(totjobs, totkau)

    # Set up the tables for the summary data
    appUseT = pt.PrettyTable(['App', 'Users', 'Jobs', '% Jobs', 'Usage [kAU]', '% Usage'])
    appStatT = pt.PrettyTable(['App', 'Min', 'Q1', 'Median', 'Q3', 'Max', 'Mean Size by Use'])

    # Loop over codes getting total usage
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
            useD = {}
            jobD = {}
            for time in timeBinsA:
                for size in sizeBinsA:
                    useD[(time, size)] = 0.0
                    jobD[(time, size)] = 0
            for size in sizeBinsA:
                useD[('>', size)] = 0.0
                jobD[('>', size)] = 0

            for rowA in appDataA:
                nodes = rowA[0]
                runtime  = rowA[1]
                jobs  = rowA[2]
                use = rowA[3]
                useSum += use
                if qval[0] >= useSum: quartiles[0] = nodes
                if qval[1] >= useSum: quartiles[1] = nodes
                if qval[2] >= useSum: quartiles[2] = nodes
                jtime = '>'
                if runtime <= max(timeBinsA):
                    for time in timeBinsA:
                        jtime = time
                        if runtime <= time: break
                jsize = 1
                for size in sizeBinsA:
                    jsize = size
                    if nodes <= size: break
                useD[(jtime, jsize)] += use
                jobD[(jtime, jsize)] += jobs
            print "\n{0}:".format(app.name)
            ru.printMatrix(sizeBinsA, "Size [Nodes]", timeBinsA + ['>'], "Runtime [h]", useD, "Usage [kAU]")
            ru.printMatrix(sizeBinsA, "Size [Nodes]", timeBinsA + ['>'], "Runtime [h]", jobD, "Jobs")

            meanByUse = appTotWeight/appTotUse
            
            pJob = 100.0 * appSumA[2]/totjobs
            pUse = 100.0 * appSumA[3]/totkau
            appUseT.add_row([app.name, appUsers, appSumA[2], pJob, appSumA[3], pUse])
            appStatT.add_row([app.name, appMinA[0]] + quartiles + [appMaxA[0], meanByUse])
        xq.dropView(xaltC, appV)

    appUseT.sortby = 'Usage [kAU]'
    appUseT.reversesort = True
    appUseT.align = "r"
    appUseT.align["App"] = "c"
    appUseT.float_format['Jobs'] = '.0'
    appUseT.float_format['% Jobs'] = '.2'
    appUseT.float_format['Usage [kAU]'] = '.3'
    appUseT.float_format['% Usage'] = '.2'
    print '\nApplication usage:'
    print appUseT, '\n'

    appStatT.sortby = 'Median'
    appStatT.reversesort = True
    appStatT.align = "r"
    appStatT.align["App"] = "c"
    appStatT.float_format['Min'] = '.0'
    appStatT.float_format['Max'] = '.0'
    appStatT.float_format['Mean Size by Job'] = '.2'
    appStatT.float_format['Mean Size by Use'] = '.2'
    print '\nApplication size statistics (all sizes in nodes, weighted by usage):'
    print appStatT, '\n'


    if useView:
       xq.dropView(xaltC, xaltRunT)
    
    # Close the database and exit nicely
    xaltDB.close()
    sys.exit(0)

def printMatrix(catXA, labelX, catYA, labelY, matrixD):
    """Print a numerical matrix of results nicely
    """
    matrixT = pt.PrettyTable([''] + catXA + ['Total', '%'])
    tot = np.sum(matrixD.values())
    ySumA = {}
    for x in catXA:
        ySumA[x] = 0
    for y in catYA:
        xA = [y]
        xSum = 0
        for x in catXA:
            val = matrixD[(y, x)]
            xSum += val
            ySumA[x] += val
            xA.append(val)
        xA.append(xSum)
        px = 100.0 * (xSum/tot)
        xA.append(px)
        matrixT.add_row(xA)
    totRowA = ['Total']
    pRowA = ['%']
    for x in catXA:
        totRowA.append(ySumA[x])
        pRowA.append(100.0*ySumA[x]/tot)
    matrixT.add_row(totRowA + [tot, 100])
    matrixT.add_row(pRowA + [100.0, ''])

    matrixT.align = "r"
    matrixT.align[''] = "c"
    matrixT.float_format = '.3'
    print matrixT

if __name__ == "__main__":
    main(sys.argv[1:])

