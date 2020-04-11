#!/bin/bash
set -e

# Make a colon (:) separated list of *.yml files under SQUEALY_BASE_DIR
#
# The script is complicated, so here is a breakdown
# 1. Find all yml files in SQUEALY_BASE_DIR (the find command)
# 2. Concatenate them into a string with : as separator (the tr command)
# 3. We get an extra colon at the end of the string, which we have to remove ...
#      the command "rev | cut -c2- | rev" is essentially removing the last colon
#      It first reverses the string, removes the first character, and then reverses it again
# 4. The output is saved in the variable FILES_TO_WATCH
# 5. Finally, we pass the list of files to flask run command
# 
# This would have been much easier if flask run supported watching a directory
# The docs say it does, but for some reason it didn't work when we tried, hence this crazy hack
# 
# NOTE: This cannot detect new files, for that you would have to restart.

FILES_TO_WATCH=$(find $SQUEALY_BASE_DIR -type f -name "*.yml" | tr '\n' ':' | rev | cut -c2- | rev)
exec flask run --extra-files=$FILES_TO_WATCH
