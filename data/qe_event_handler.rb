## Custom automation script for CFME
# Original author: mawagner
# Modified to work with more object types: mfalesni
# example PUT call: curl X PUT http://localhost:8080/events/VmRedhat/vm_name?event=vm_power_on
# example PUT call: curl X PUT http://localhost:8080/events/EmsRedhat/ems_name?event=ems_auth_changed
# example PUT call: curl X PUT http://localhost:8080/events/host/hostname_of_host?event=host_analysis_complete
# example GET call (for debugging only): curl X GET http://localhost:8080/events
require "rest-client"


##
# Call this method to reveal all key/values of the 'root' and 'object' objects.
def print_debug_info
    $evm.root.attributes.sort.each { |k, v| $evm.log("info", "#### Root #{k}: #{v}")}
    $evm.object.attributes.sort.each { |k, v| $evm.log("info", "#### Object #{k}: #{v}")}
end
 
 
def base_url
    url = "http://#{$evm.object['url']}:#{$evm.object['port']}/#{$evm.object['route1']}"
end
 
def suffix
    "?event=#{$evm.root['event']}"
end
 
def put *opts 
    response = RestClient.put(opts.join('/') + suffix, "")
    $evm.log("info", "API Call: #{opts.join('/')}#{suffix}")
    $evm.log("info", "API Response: #{response.code}")
end

#
# Automate Method
#
$evm.log("info", "Custom Automate Method Started")
otype = $evm.root["vmdb_object_type"].to_s
if otype == "vm"
    $evm.log("info", "Relaying VM event")
    vm = $evm.root['vm']
    mgmt_sys = $evm.root['ext_management_system']
     
    if !mgmt_sys.nil?
        put(base_url, CGI::escape(mgmt_sys.type), CGI::escape(mgmt_sys.name))
    elsif !vm.nil?
        put(base_url, CGI::escape(vm.type), CGI::escape(vm.name))
    else
        $evm.log(:warn, "Could not execute the RelayEvent query")
    end
elsif !$evm.root["vmdb_object_type"].nil?   # original one because nil.to_s == ''
    $evm.log("info", "Relaying #{otype} event (generic):")
    put(base_url, CGI::escape(otype), CGI::escape($evm.root[otype].name))
else
    $evm.log(:warn, "Could not determine the vmdb object!")
end

$evm.log("info", "Custom Automate Method Ended")
exit MIQ_OK