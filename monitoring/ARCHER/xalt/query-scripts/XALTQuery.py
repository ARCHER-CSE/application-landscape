#
# Python module with base functions for querying the XALT database
#
import MySQLdb
import prettytable as pt

def getUserProjectMap(xaltC):
    """Generate list of known users and their groups from database

    Args:
        xaltC (MySQLdb.cursor): The MySQL DB cursor

    Returns:
        userProjectMapD (dict, string): Dictionary of projects by usernames
    """
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


#####################################################################
# Functions for querying total usage
#####################################################################
def getTotUse(xaltC, xaltRunT):
    """Get the total jobs and usage by all jobs in the table.
    """
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
            FROM {0}
    ) AS T
    ;
    """.format(xaltRunT)
    try:
       xaltC.execute(query)
       results = xaltC.fetchone()
       totjobs = results[0]
       totkau = results[1]
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get total stats"

    return (totjobs, totkau)

#####################################################################
# Functions for querying application usage
#####################################################################
def updateAppName(xaltC, appName, appRegexp):
    """Get the number of users from app view
    """
    query = """
UPDATE
    xalt_run
    SET
        app = "{0}"
    WHERE
        exec_path REGEXP "{1}"
    AND
        app is NULL
    """.format(appName, appRegexp)
    try:
       xaltC.execute(query)
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to set application name"

def getAppUsers(xaltC, xaltAppV):
    """Get the number of users from app view
    """
    appUsers = None
    query = """
SELECT
    COUNT(DISTINCT(user))
    FROM {0}
    """.format(xaltAppV)
    try:
       xaltC.execute(query)
       results = xaltC.fetchone()
       appUsers = results[0]
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get application users"
       dropView(xaltC, xaltAppV)
       return None

    return appUsers

def getAppData(xaltC, xaltAppV):
    """Get the total jobs and usage from application view
    """
    results = None
    query = """
SELECT 
    Nodes,
    WalltimeH,
    COUNT(1) AS Jobs,
    SUM(0.36*run_time*Nodes/3600) AS kAU,
    SUM(0.36*run_time*Nodes*Nodes/3600) AS Weight
    FROM (
        SELECT
            uuid,
            run_time,
            CEIL(run_time/3600) AS WalltimeH,
            CASE
                WHEN tasks_per_node > 0 THEN
                   CEIL(num_cores/tasks_per_node)
                WHEN num_cores < 24 THEN
                   1
                ELSE
                   CEIL(num_cores/24)
            END as Nodes
            FROM {0}
    ) AS T
    GROUP BY Nodes, WalltimeH
    ORDER BY Nodes
    """.format(xaltAppV)
    try:
       xaltC.execute(query)
       results = xaltC.fetchall()
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get total stats"
       dropView(xaltC, xaltAppV)
       return None

    return results

#####################################################################
# Functions for querying linker usage
#####################################################################
def getNullLinkerUse(xaltC, xaltRunT):
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
            FROM {0}
            WHERE uuid IS NULL
    ) AS T
    GROUP BY uuid;
    """.format(xaltRunT)
    try:
       xaltC.execute(query)
       results = xaltC.fetchone()
       nulljobs = results[1]
       nullkau = results[2]
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get NULL linker summary"

    return (nulljobs, nullkau)

def printTotalLinkerStats(xaltC, xaltRunT):
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
            FROM xalt_link, {0}
            WHERE xalt_link.uuid = {0}.uuid
    ) AS T
    GROUP BY link_program;
    """.format(xaltRunT)
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
    resLinkT = pt.PrettyTable([''] + compileSuiteA + ['Total'])
    resUseT = pt.PrettyTable([''] + compileSuiteA + ['Total'])
    resJobsT = pt.PrettyTable([''] + compileSuiteA + ['Total'])
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

    print "\nAll link events: compiler suite vs. compiler language:"
    resLinkT.align = "r"
    print resLinkT, "\n"
    print "Unidentified link events: {}\n".format(other)

    print "\nLimited run usage [kAU] (for known link events): compiler suite vs. compiler language"
    resUseT.align = "r"
    resUseT.float_format = '.3'
    print resUseT, "\n"

    print "Unidentified usage: {}\n".format(otherUse)

    print "\nLimited jobs (for known link events): compiler suite vs. compiler language"
    resJobsT.align = "r"
    print resJobsT, "\n"

    print "Unidentified jobs: {}\n".format(otherJobs)

#####################################################################
# Functions for querying hybrid job stats
#####################################################################
def printTotalHybridStats(xaltC, xaltRunT, totjobs, totkau):
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
            FROM {0}
    ) AS T
    GROUP BY num_threads, Nodes
    ;
    """.format(xaltRunT)
    try:
       xaltC.execute(query)
       results = xaltC.fetchall()
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to get hybrid job data"
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

    resUseT = pt.PrettyTable([''] + sizeBinsA + ['Total', '%'])
    resJobT = pt.PrettyTable([''] + sizeBinsA + ['Total', '%'])
    sizeUseSumA = len(sizeBinsA) * [0.0]
    sizeJobSumA = len(sizeBinsA) * [0]
    totUse = 0.0
    totJob = 0
    for i in range(maxthread):
       useA = [i+1]
       jobA = [i+1]
       tUse = 0.0
       tJob = 0
       for j, size in enumerate(sizeBinsA):
          use = usageD[(i+1, size)]
          job = jobsD[(i+1, size)]
          totUse += use
          totJob += job
          sizeUseSumA[j] += use
          sizeJobSumA[j] += job
          tUse += use
          tJob += job
          useA.append(use)
          jobA.append(job)
       useA.append(tUse)
       jobA.append(tJob)
       pUse = 100.0 * (tUse/totkau)
       pJob = 100.0 * (float(tJob)/totjobs)
       useA.append(pUse)
       jobA.append(pJob)
       if tJob > 0:
          resUseT.add_row(useA)
          resJobT.add_row(jobA)
    pUse = 100.0 * (totUse/totkau)
    pJob = 100.0 * (float(totJob)/totjobs)
    resUseT.add_row(['Total'] + sizeUseSumA + [totUse, pUse])
    resUseT.add_row(['%'] + [100.0*x/totkau for x in sizeUseSumA] + [100.0*totUse/totkau, ''])
    resJobT.add_row(['Total'] + sizeJobSumA + [totJob, pJob])
    resJobT.add_row(['%'] + [100.0*float(x)/totjobs for x in sizeJobSumA] + [100.0*float(totJob)/totjobs, ''])

    print "\nUsage (in kAU): job size [Nodes] vs. number of threads:"
    resUseT.align = "r"
    resUseT.float_format = '.3'
    resUseT.float_format['%'] = '.2'
    print resUseT
    print "\nJobs: job size [Nodes] vs. number of threads:"
    resJobT.align = "r"
    resJobT.float_format = '.2'
    print resJobT

#####################################################################
# Functions for creating and droppong views
#####################################################################
def createRunView(xaltC, prop, val):
    """Create DB view of jobs belonging to specified project

    """
    viewName = prop + "_run_view"
    query = 'CREATE VIEW {0} AS SELECT * FROM xalt_run WHERE {1} REGEXP "{2}"'.format(viewName, prop, val)
    try:
       xaltC.execute(query)
       return viewName
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to create VIEW"
       return None

def dropView(xaltC, viewName):
    """Drop specified VIEW from DB
    """
    query = 'DROP VIEW {0}'.format(viewName)
    try:
       xaltC.execute(query)
       return True
    except MySQLdb.Error, e:
       print ("Error %d: %s" % (e.args[0], e.args[1]))
       print "Unable to drop VIEW {0}".format(viewName)
       return False


