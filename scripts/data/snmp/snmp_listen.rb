#!/usr/bin/env ruby
# Author: mfalesni
require "rubygems"
require "snmp"
require "json"
require "webrick"
require "thread"

# modify the classes to be able to serialise to json
# they serialize as strings by default
# so we learn them how to serialize as json
class SNMP::SNMPv1_Trap
    def to_json *args
        {
            :trap_version => 1,
            :enterprise => enterprise.to_s,
            :agent_addr => agent_addr.to_s,
            :generic_trap => generic_trap,
            :specific_trap => specific_trap,
            :timestamp => timestamp.to_s,
            :source_ip => source_ip,
            :vars => varbind_list.collect { |var|
                {
                    :name => var.name.to_str,
                    :oid => var.oid.to_str,
                    :value => var.value
                }
            }
        }.to_json *args
    end
end

class SNMP::SNMPv2_Trap
    def to_json *args
        {
            :trap_version => 2,
            :oid => trap_oid.to_s,
            :source_ip => source_ip,
            :vars => vb_list.collect { |var|
                {
                    :name => var.name.to_str,
                    :oid => var.oid.to_str,
                    :value => var.value
                }
            }
        }.to_json *args
    end
end

# Ugly global vars but ruby does not have lexical scope and I am not ruby pro ...
$TRAPS = []
$TRAPS_MUTEX = Mutex.new

snmp_listener = SNMP::TrapListener.new :Port => 162, :Community => 'public' do |manager|
    # Collect all traps into the array
    manager.on_trap_default do |trap|
        $TRAPS_MUTEX.synchronize do
            $TRAPS << trap
        end
    end
end

class TrapServer < WEBrick::HTTPServlet::AbstractServlet
  def do_GET request, response
    if request.path == "/traps"
        response.status = 200
        response['Content-Type'] = 'text/javascript'
        $TRAPS_MUTEX.synchronize do
            response.body = {:status => 200, :content => $TRAPS}.to_json
        end
    elsif request.path == "/flush"
        response.status = 200
        response['Content-Type'] = 'text/javascript'
        $TRAPS_MUTEX.synchronize do
            response.body = {:status => 200, :content => $TRAPS}.to_json
            $TRAPS.clear
        end
    else
        response.status = 404
        response['Content-Type'] = 'text/javascript'
        response.body = {:status => 404, :content => "Unknown route: #{request.path}"}.to_json
    end
  end
end

# To be run in the threads
listener = Thread.new do
    snmp_listener.join
end

server = Thread.new do
    webrick = WEBrick::HTTPServer.new :Port => 8765
    webrick.mount '/', TrapServer
    trap "INT" do
        server.stop
    end
    webrick.start
end

listener.join
server.join
