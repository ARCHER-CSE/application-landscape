# XALT Monitoring on ARCHER #

The XALT tool allows monitoring of both link events and run events
on an HPC system. It does this by wrapping 'ld' and the parallel
job launcher ('aprun' on ARCHER). XALT is Open Source and can be
found at:

* https://sourceforge.net/projects/xalt/

In this document we describe:

* Modifications made to standard XALT (v 0.6.0) to suit requirements
  for ARCHER.
* The setup and location of XALT resources on ARCHER.
* The build and install procedure we used.

## Reasons for Modifications to XALT for ARCHER ##

We made a number of modifications to the standard XALT source for use
on ARCHER. These changes were to achieve 3 aims that were not already
covered by the XALT tool:

1. Monitor additional runtime properties: tasks per node, tasks per 
   socket, hardware threads, full job launch line.
2. Allow for a custom locaiton for the JSON files produced by XALT
   when using the file transmission method. Also allow for custom
   umask settings for files and directories created by XALT. This
   is to allow a user other than root to access and remove the
   files.
3. Cut down the number of environment variables captured by using
   a whitelist of variables to capture rather than a blacklist of
   those to skip.

The actual modifications are further documented below and patch files
are also provided.

## XALT Setup on ARCHER ##

XALT on ARCHER is setup across two different hosts:

* On the ARCHER Cray XC system for generating link and run data.
* On a separate VM used for archiving the XALT JSON data, hosting the
  XALT database and ingesting the JSON data into the databse.

### XALT ARCHER Data Flow ###

1. When a user links or runs (using aprun) then a JSON file is written
   to "/home/y07/y07/xalt/${USER}".
2. Twice a day these JSON files are synced to the "archer-logs,epcc.ed.ac.uk"
   VM using a cron job running on the VM.
3. Twice a day the data in the JSON files are ingested into the XALT
   database and then archived (using zip) to save space. This is done
   by the "xalt_ingest_and_archive.bash" script.

### crontab on DB server ###

The dataflow was designed so that no cron processes are required to run
on ARCHER itself. Instead, the DB server logs into ARCHER periodically
and collects new JSON files (removing them as it goes).

Once the data has been moved across to the DB server another crontab
entry ingests the data into the XALT database.

The crontab in this repository shows the commands used.

## Building and installing XALT for ARCHER ##

### Build and Install ###

The standard build instructions for XALT from the documentation were 
followed to install XALT on ARCHER in "/home/y07/y07/cse/xalt/0.6.0".

### Changes to the source ###

Once the standard install was completed we made the changes required to 
customise the environment for ARCHER.

The patch file in this repository describe the changes made to the XALT 0.6.0
source for ARCHER.

### Changes to the XALT database ###

A number of additional columns were added to the "xalt_run" table in the 
XALT database to accommodate the additional data fields collected by our
custom installation. These are:

* tasks_per_node: int(11)
* tasks_per_socket: int(11)
* hw_threads: int(11)
* launch_command: varchar(1024)

### Create the XALT modulefile ###

The "xalt" module sets the following environment variables:

* ALT_LINKER=/home/y07/y07/cse/xalt/0.6.0/bin/ld
* XALT_TRANSMISSION_STYLE=file
* XALT_ETC_DIR=/home/y07/y07/cse/xalt/0.6.0/etc 
* XALT_DIR=/home/y07/y07/cse/xalt/0.6.0 
* XALT_FILE_TRANSMIT_LOC=/home/y07/y07/xalt/${USER}

and adds the following paths:

* PATH += /home/y07/y07/cse/xalt/0.6.0/bin 
* PATH += /home/y07/y07/cse/xalt/0.6.0/libexec 
* PYTHONPATH += /home/y07/y07/cse/xalt/0.6.0/libexec 
* PYTHONPATH += /home/y07/y07/cse/xalt/0.6.0/site 
