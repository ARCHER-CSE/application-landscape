#!/usr/bin/env python
#
# Generate useful statistics from the XALT database
#
import MySQLdb
import sys
import prettytable as pt
import csv

def main(argv):

    dbConfigF = open(sys.argv[1].strip(), "r")
    host, user, passwd, dbname, sockloc = dbConfigF.readline().split()
    dbConfigF.close()

    xaltDB = MySQLdb.connect(host, user, passwd, dbname, unix_socket=sockloc)
    xaltC = xaltDB.cursor()

    # Generate list of known users and their groups
    userProjectMapD = getUserProjectMap(xaltDB, xaltC)

    # Read project details
    projAreaD, projTypeD, projFundD = readProjectCSV('safe_project_list.csv')
    for code in projAreaD:
       print code, projAreaD[code], projFundD[code]
    
    # Get summary of data with no linker stats
    nulljobs, nullkau = getNullLinkerUse(xaltDB, xaltC)
    print '\nLink event not identified:\n\tJobs = {:d}\n\t kAU = {:.3f}'.format(nulljobs, nullkau)

    # Print total linker event statistics
    printTotalLinkerStats(xaltDB, xaltC)
    
    # Close the database and exit nicely
    xaltDB.close()
    sys.exit(0)

def readProjectCSV(infile):
    # Read project metadata from CSV file
    projAreaD = {}
    projTypeD = {}
    projFundD = {}
    with open(infile, 'r') as csvfile:
       projectR = csv.reader(csvfile)
       for row in projectR:
          code = row[0].strip()
          projAreaD[code] = row[1].strip()
          projTypeD[code] = row[2].strip()
          projFundD[code] = row[3].strip()
    return (projAreaD, projTypeD, projFundD)

def getUserProjectMap(xaltDB, xaltC):
    # Generate list of known users and their groups
    userProjectMapD = {}
    query = "SELECT user, account, count(*) FROM xalt_run GROUP BY user, account"
    try:
       xaltC.execute(query)
       results = xaltC.fetchall()
       for row in results:
          username = row[0]
          project = row[1].split('-')[0]
          if project == "unknown" or project == "":
             continue
          if username in userProjectMapD:
             if project not in userProjectMapD[username]:
                userProjectMapD[username] += ':{}'.format(project)
          else:
             userProjectMapD[username] = project
 
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to generate user -> project map"

    return userProjectMapD

# Get total jobs and usage where the link event is not identified
def getNullLinkerUse(xaltDB, xaltC):
    nulljobs = 0
    nullkau = 0.0
    query = """
SELECT 
    uuid,
    COUNT(1) AS Jobs,
    SUM(0.36*run_time*Nodes/3600) AS kAU
    FROM (
        SELECT
            uuid,
            run_time,
            CASE
                WHEN tasks_per_node > 0 THEN
                   CEIL(num_cores/tasks_per_node)
                WHEN num_cores < 24 THEN
                   1
                ELSE
                   CEIL(num_cores/24)
            END as Nodes
            FROM xalt_run
            WHERE uuid IS NULL
    ) AS T
    GROUP BY uuid;
    """
    try:
       xaltC.execute(query)
       results = xaltC.fetchone()
       nulljobs = results[1]
       nullkau = results[2]
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get NULL linker summary"

    return (nulljobs, nullkau)

def printTotalLinkerStats(xaltDB, xaltC):
    # Get summary of linker statistics
    compileSuiteA = ['Cray', 'Intel', 'GCC']
    compileLangA = ['Fortran', 'C', 'C++']
    compilerMapD = {
               'ftn_driver': ('Cray', 'Fortran'),
               'driver.cc': ('Cray', 'C'),
               'c++': ('Cray', 'C++'),
               'ifort': ('Intel', 'Fortran'),
               'icc': ('Intel', 'C'),
               'icpc': ('Intel', 'C++'),
               'gfortran': ('GCC', 'Fortran'),
               'gcc': ('GCC', 'C'),
               'g++': ('GCC', 'C++')
                     }
    # Get the number of link events 
    linkerStatsD = {}
    for key, value in compilerMapD.iteritems():
       linkerStatsD[value] = 0
    other = 0
    query = "SELECT link_program, count(*) FROM xalt_link GROUP BY link_program"
    try:
       xaltC.execute(query)
       results = xaltC.fetchall()
       for row in results:
          linker = row[0]
          count = row[1]
          if linker in compilerMapD:
             linkerStatsD[compilerMapD[linker]] = count
          else:
             other += count
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get linker summary"

    # Get usage associated with link events
    linkerUseD = {}
    linkerJobsD = {}
    for key, value in compilerMapD.iteritems():
       linkerUseD[value] = 0
       linkerJobsD[value] = 0
    otherUse = 0
    otherJobs = 0
    query = """
SELECT 
    link_program,
    COUNT(1) AS Jobs,
    SUM(0.36*run_time*Nodes/3600) AS kAU
    FROM (
        SELECT
            link_program,
            run_time,
            CASE
                WHEN tasks_per_node > 0 THEN
                   CEIL(num_cores/tasks_per_node)
                WHEN num_cores < 24 THEN
                   1
                ELSE
                   CEIL(num_cores/24)
            END as Nodes
            FROM xalt_link, xalt_run
            WHERE xalt_link.uuid = xalt_run.uuid
    ) AS T
    GROUP BY link_program;
    """
    try:
       xaltC.execute(query)
       results = xaltC.fetchall()
       for row in results:
          linker = row[0]
          jobs = row[1]
          nh = row[2]
          if linker in compilerMapD:
             linkerUseD[compilerMapD[linker]] = nh
             linkerJobsD[compilerMapD[linker]] = jobs
          else:
             otherUse += nh
             otherJobs += jobs
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get linker usage data"
    
    # Accummulate the results into tables
    suiteSumD = {}
    suiteUseD = {}
    suiteJobsD = {}
    for suite in compileSuiteA:
       suiteSumD[suite] = 0
       suiteUseD[suite] = 0
       suiteJobsD[suite] = 0
    resLinkT = pt.PrettyTable(['Language'] + compileSuiteA + ['Total'])
    resUseT = pt.PrettyTable(['Language'] + compileSuiteA + ['Total'])
    resJobsT = pt.PrettyTable(['Language'] + compileSuiteA + ['Total'])
    for lang in compileLangA:
       langSum = 0
       langUse = 0
       langJob = 0
       resA = [lang]
       useA = [lang]
       jobA = [lang]
       for suite in compileSuiteA:
          langSum += linkerStatsD[(suite, lang)]
          langUse += linkerUseD[(suite, lang)]
          langJob += linkerJobsD[(suite, lang)]
          suiteSumD[suite] += linkerStatsD[(suite, lang)]
          suiteUseD[suite] += linkerUseD[(suite, lang)]
          suiteJobsD[suite] += linkerJobsD[(suite, lang)]
          resA.append(linkerStatsD[(suite, lang)])
          useA.append(linkerUseD[(suite, lang)])
          jobA.append(linkerJobsD[(suite, lang)])
       resLinkT.add_row(resA + [langSum]) 
       resUseT.add_row(useA + [langUse]) 
       resJobsT.add_row(jobA + [langJob]) 
    tot = 0
    totUse = 0
    totJobs = 0
    resA = ['Total']
    useA = ['Total']
    jobA = ['Total']
    for suite in compileSuiteA:
       tot += suiteSumD[suite]
       totUse += suiteUseD[suite]
       totJobs += suiteJobsD[suite]
       resA.append(suiteSumD[suite])
       useA.append(suiteUseD[suite])
       jobA.append(suiteJobsD[suite])
    resLinkT.add_row(resA + [tot]) 
    resUseT.add_row(useA + [totUse]) 
    resJobsT.add_row(jobA + [totJobs]) 

    print "\nLink events broken down by compile langauge and compiler suite:"
    resLinkT.align = "r"
    resLinkT.align["Language"] = "c"
    print resLinkT, "\n"
    print "Unidentified link events: {}\n".format(other)

    print "\nRun usage (in kAU) broken down by compile langauge and compiler suite:"
    resUseT.align = "r"
    resUseT.align["Language"] = "c"
    resUseT.float_format = '.3'
    print resUseT, "\n"

    print "Unidentified usage: {}\n".format(otherUse)

    print "\nJobs broken down by compile langauge and compiler suite:"
    resJobsT.align = "r"
    resJobsT.align["Language"] = "c"
    print resJobsT, "\n"

    print "Unidentified jobs: {}\n".format(otherJobs)

if __name__ == "__main__":
    main(sys.argv[1:])

