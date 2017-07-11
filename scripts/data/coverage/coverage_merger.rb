# goes into the rails root
# merges coverage results from multiple processes, potentially on multiple appliances
# This expects the layout used by our coverage hook: "RAILS_ROOT/coverage/[ipaddress]/[pid]/"
# It does the report merging manually based on that layout, and can be run at any time
# to compile reports.
require 'fileutils'
require 'json'
require 'simplecov'
require 'simplecov/result'

rails_root = '/var/www/miq/vmdb'
results = Hash.new
coverage_root = "/var/www/miq/vmdb/coverage"
puts "Scanning for results in #{coverage_root}"
json_files = Dir.glob(
  File.join(coverage_root, "*", "*", ".resultset.json")
)
merged_dir = File.join(coverage_root, 'merged')

for json_file in json_files
  begin
    json = File.read(json_file)
    results.update(JSON.parse(json))
    puts "Merging #{json_file}"
  rescue
    puts "Skipping #{json_file}, no valid JSON"
  end
end

if results.empty?
  abort "No results found for merging."
else
  puts "All results merged, compiling report."
end

FileUtils.mkdir_p(merged_dir)
File.open(File.join(merged_dir, '.resultset.json'), "w") do |f|
  JSON.dump(results, f)
end

# Set up simplecov to use the merged results, then fire off the formatters
SimpleCov.project_name 'CFME'
SimpleCov.root '/'
SimpleCov.coverage_dir merged_dir
SimpleCov.instance_variable_set("@result", SimpleCov::Result.from_hash(results))
SimpleCov.formatters = SimpleCov::Formatter::HTMLFormatter
SimpleCov.use_merging true
SimpleCov.merge_timeout 2 << 28
# Remove the original filters
SimpleCov.filters.clear
SimpleCov.add_filter do |src|
  include_file = src.filename =~ /^#{rails_root}/
  unless include_file
    include_file = src.filename =~ /manageiq-/
  end
  ! include_file
end
SimpleCov.add_group "REST API", "app/controllers/api"
SimpleCov.add_group "Models", "app/models"
SimpleCov.add_group "Automate Engine", "lib/miq_automation_engine"
SimpleCov.result.format!
