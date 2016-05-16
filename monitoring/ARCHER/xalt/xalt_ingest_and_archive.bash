#!/bin/bash
#
# Script to ingest XALT JSON files into the XALT DB and then archive
# the data that has been ingested.
#
# EPCC, The University of Edinburgh, 2016
#

# e-mail address for status messages
statusmail="nobody@epcc.ed.ac.uk"

# Setup the environment
source ${HOME}/config/anaconda.config
source ${HOME}/config/xalt.config

# Location for XALT archive
XALT_ARCHIVE_LOC=${HOME}/xalt_logs_archive
XALT_FILE_TRANSMIT_LOC=${HOME}/xalt_logs

# Dates
nowdate=$(date --rfc-3339=date)
nowyear=$(date +%Y)

# Script logging location
logfile="${HOME}/logs/ingest/${nowyear}/${nowdate}_archive.log"

# Ingest the data
ingest_res=$(xalt_file_to_db.py 2>&1)
echo $ingest_res >> ${logfile}

# Archive the files we have just ingested
archivefile="${XALT_ARCHIVE_LOC}/${nowyear}/xalt_archive_${nowdate}.zip"
zip -qrmT ${archivefile} ${XALT_FILE_TRANSMIT_LOC}/* >> ${logfile} 2>&1

# Mail the status of this event 
if [[ $? -ne 0 ]]
then
   statusmsg="Archive of XALT failed: $nowdate, $ingest_res, $logfile"
   echo -e $statusmsg | mail -s "XALT Archive Error" "${statusmail}"
else
   statusmsg="Archive of XALT success: $nowdate, ${archivefile}, $ingest_res, $logfile"
   echo -e $statusmsg | mail -s "XALT Archive Success" "${statusmail}"
fi

exit 0

