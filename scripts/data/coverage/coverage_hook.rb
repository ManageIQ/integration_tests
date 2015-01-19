# goes in rails config dir, then require it from boot.rb

# set up simplecov, broken out by process for recombining later
require 'appliance_console/env'
require 'fileutils'
require 'simplecov'
require 'yaml'

rails_root = File.expand_path(File.join(File.dirname(__FILE__), "..", "vmdb"))
SimpleCov.start 'rails' do
  # Set the coverage dir for this process to "RAILS_ROOT/coverage/[ipaddress]/[pid]/"
  coverage_dir File.join(rails_root, "coverage", ApplianceConsole::Env["IP"], Process.pid.to_s)
  # make sure coverage_dir exists
  FileUtils.mkdir_p(SimpleCov.coverage_dir)
  # coverage root is one level below the rails root so we pick up vmdb/../lib
  root File.join(rails_root, '..')
  # This needs to be unique per simplecov runner
  command_name "%s-%s" % [ApplianceConsole::Env["IP"], Process.pid]
end
