# goes into the rails root
# merges coverage results from multiple processes, potentially on multiple appliances
# This expects the layout used by our coverage hook: "RAILS_ROOT/coverage/[ipaddress]/[pid]/"
# It does the report merging manually based on that layout, and can be run at any time
# to compile reports.
require 'fileutils'
require 'json'
require 'simplecov'
require 'simplecov/result'

results = Hash.new
coverage_root = File.join(File.expand_path(Rails.root), "coverage")
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
end

FileUtils.mkdir_p(merged_dir)
File.open(File.join(merged_dir, '.resultset.json'), "w") do |f|
  JSON.dump(results, f)
end

# Set up simplecov to use the merged results, then fire off the formatters
SimpleCov.coverage_dir merged_dir
SimpleCov.instance_variable_set("@result", SimpleCov::Result.from_hash(results))
SimpleCov.formatters = SimpleCov::Formatter::HTMLFormatter
SimpleCov.use_merging true
SimpleCov.merge_timeout 2 << 28
SimpleCov.add_group "APIs", "vmdb/app/apis"
SimpleCov.add_group "Presenters", "vmdb/app/presenters"
SimpleCov.add_group "Services", "vmdb/app/services"
SimpleCov.result.format!
