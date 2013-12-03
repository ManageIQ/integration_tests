# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Description: script to get the pgsession count
# Author: Aziza Karol <akarol@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BEGIN {
        }
/ count $/ {     
              getline # bypass the line of underscores
              getline # get the count of sessions
			count = int($1)
              print  $1
              exit count- 1   
            }
END {
        
        }
