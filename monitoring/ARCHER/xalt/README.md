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

## Building and installing XALT for ARCHER ##

