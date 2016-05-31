#!/usr/bin/env python
#
# Generate useful statistics from the XALT database
#
import MySQLdb
import sys
import prettytable as pt

def main(argv):

    dbConfigF = open(sys.argv[1].strip(), "r")
    host, user, passwd, dbname, sockloc = dbConfigF.readline().split()
    dbConfigF.close()

    xaltDB = MySQLdb.connect(host, user, passwd, dbname, unix_socket=sockloc)
    xaltC = xaltDB.cursor()
     
    # Generate list of known users and their groups
    userProjectMapD = getUserProjectMap(xaltDB, xaltC)
    
    # Get total data
    totjobs, totkau = getTotUse(xaltDB, xaltC)
    print '\nTotal usage and jobs:\n\tJobs = {:d}\n\t kAU = {:.3f}'.format(totjobs, totkau)

    # Get hybrid job event statistics
    printTotalHybridStats(xaltDB, xaltC)
    
    # Close the database and exit nicely
    xaltDB.close()
    sys.exit(0)

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
def getTotUse(xaltDB, xaltC):
    totjobs = 0
    totkau = 0.0
    query = """
SELECT 
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
    ) AS T
    ;
    """
    try:
       xaltC.execute(query)
       results = xaltC.fetchone()
       totjobs = results[0]
       totkau = results[1]
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get total stats"

    return (totjobs, totkau)

def printTotalHybridStats(xaltDB, xaltC):
    query = """
SELECT 
    num_threads,
    Nodes,
    COUNT(1) AS Jobs,
    SUM(0.36*run_time*Nodes/3600) AS kAU
    FROM (
        SELECT
            num_threads,
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
    ) AS T
    GROUP BY num_threads, Nodes
    ;
    """
    try:
       xaltC.execute(query)
       results = xaltC.fetchall()
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get linker summary"
       return

    maxthread = 48
    sizeBinsA = [1, 2, 3, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]
    usageD = {}
    jobsD = {}

    for i in range(maxthread):
        for size in sizeBinsA:
           usageD[(i+1, size)] = 0.0
           jobsD[(i+1, size)] = 0
   
    for row in results:
       nthread = row[0]
       if nthread == 0:
          nthread = 1
       elif nthread > maxthread:
          nthread = maxthread
       nnode = row[1]
       njobs = row[2]
       kau = row[3]
       for size in sizeBinsA:
          if nnode <= size:
             usageD[(nthread, size)] += kau 
             jobsD[(nthread, size)] += njobs 
             break

    resUseT = pt.PrettyTable(['Threads'] + sizeBinsA + ['Total'])
    resJobT = pt.PrettyTable(['Threads'] + sizeBinsA + ['Total'])
    sizeUseSumD = {}
    sizeJobSumD = {}
    for size in sizeBinsA:
       sizeUseSumD[size] = 0.0
       sizeJobSumD[size] = 0
    totUse = 0.0
    totJob = 0
    for i in range(maxthread):
       useA = [i+1]
       jobA = [i+1]
       tUse = 0.0
       tJob = 0
       for size in sizeBinsA:
          use = usageD[(i+1, size)]
          job = jobsD[(i+1, size)]
          totUse += use
          totJob += job
          sizeUseSumD[size] += use
          sizeJobSumD[size] += job
          tUse += use
          tJob += job
          useA.append(use)
          jobA.append(job)
       useA.append(tUse)
       jobA.append(tJob)
       if tJob > 0:
          resUseT.add_row(useA)
          resJobT.add_row(jobA)
    resUseT.add_row([''] + sizeUseSumD.values() + [totUse])
    resJobT.add_row([''] + sizeJobSumD.values() + [totJob])

    print "\nUsage (in kAU) broken down by threads and job size (in Nodes):"
    resUseT.align = "r"
    resUseT.align["Threads"] = "c"
    resUseT.float_format = '.3'
    print resUseT
    print "\nJobs broken down by threads and job size (in Nodes):"
    resJobT.align = "r"
    resJobT.align["Threads"] = "c"
    print resJobT
   
          
if __name__ == "__main__":
    main(sys.argv[1:])

