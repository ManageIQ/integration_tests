# goes in rails config dir, then require it from boot.rb

# set up simplecov, broken out by process for recombining later
require 'simplecov'

rails_root = File.expand_path(File.join(File.dirname(__FILE__), "..", "vmdb"))
SimpleCov.start 'rails' do
  coverage_dir File.join(rails_root, "coverage", Process.pid.to_s)
  # coverage root is one level below the rails root so we pick up vmdb/../lib
  root File.join(rails_root, '..')
  # This needs to be unique per simplecov runner
  command_name Process.pid
  # Make this a big number, so all generated reports are merged
  merge_timeout 2 << 28
  # APIs were ungrouped, so be nice to them
  add_group "APIs", "app/apis"
  # filter non-vmdb libs out of the default libraries group
  add_group "Libraries", "vmdb/lib/"
  # match lib dir outside of vmdb, exclude util
  # will false-positive on vmdb/lib/blah/lib/something.rb...
  # bonus points for the regex that doesn't
  add_group "MIQ Libraries", "(?<!vmdb)/lib/(?!util/).*$"
  #  match lib/util by itself
  add_group "MIQ Utils", "(?<!vmdb)/lib/util/.*$"
end
