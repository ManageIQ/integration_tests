# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Description: script to get the region value
# Author: Aziza Karol <akarol@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BEGIN {
        }
/ region $/ {     
              getline # bypass the line of underscores
              getline # get the region value 
              print  $1
		region  = int($1)	
              exit region - 1   
            }
END {
        
        }
