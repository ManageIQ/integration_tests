#!/usr/bin/ruby

require "pp"

puts "Welcome to metrics threshold setter"

threshold = (ARGV[0] or "5.minutes")

config_changes = {:performance => {:capture_threshold => {:container => threshold,
                                                          :ems_cluster => threshold,
                                                          :container_group => threshold,
                                                          :container_node => threshold}}}
puts "Applying config changes:"
pp config_changes
MiqServer.my_server.set_config(config_changes)

puts "Saving configuration\n"
MiqServer.my_server.save()

puts "Done!"
