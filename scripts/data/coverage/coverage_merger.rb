# This script merges coverage results from multiple processes, potentially on multiple appliances
# This expects the layout used by our coverage hook: "coverage/[ipaddress]/[pid]/.resultset.json".
# It will look for the coverage archive either under the current directory or the one specified.
# It does the report merging manually based on that layout, and can be run at any time
# to compile reports.   
#
# The basic format of the .resultset.json files is:
#   
#   {
#       "$ip-$pid": {
#           "coverage": {
#              "$file1": {
#                   $coverage_data_line1,
#                   .
#                   .
#                   .
#                   $coverage_data_lineN
#               },
#               .
#               .
#               .
#              "$fileN": {
#                   $coverage_data_line1,
#                   .
#                   .
#                   .
#                   $coverage_data_lineN
#               },
#           }
#       }
#   } 
#
# Note coverage data is either:
#
#      - 0: line not covered
#      - > 0: Number of times line covered.
#      - null: Not coverable (e.g. a comment)
#
# The merge will actually still keep the data separate between the 
# appliance-processes, but they are all in the same file.   sonar-scanner 
# can apparently handle this fine.   So the file will look like:
# 
#   {
#       "$ip1-$pid1": {
#           "coverage": {
#               ...
#           }
#       }
#       .
#       .
#       .
#       "$ipM-$pidN": {
#           "coverage": {
#               ...
#           }
#       }
#   } 
#
require 'fileutils'
require 'json'
require 'optparse'
require 'simplecov'
require 'simplecov/result'

rails_root = '/var/www/miq/vmdb'
results = Hash.new

# Parse command line arguments:
options = {}
options[:coverage_root] = './coverage'
OptionParser.new do |parser|
  parser.on("-c", "--coverageRoot DIR", "Path to the coverage directory.") do |v|
    options[:coverage_root] = v
  end
end.parse!

puts "Scanning for results in #{options[:coverage_root]}"
json_files = Dir.glob(
  File.join(options[:coverage_root], "*", "*", ".resultset.json")
)
merged_dir = File.join(options[:coverage_root], 'merged')
merged_result_set = File.join(merged_dir, '.resultset.json')

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
  puts "All results merged, compiling report: #{merged_result_set}"
end

FileUtils.mkdir_p(merged_dir)
File.open(merged_result_set, "w") do |f|
  f.puts JSON.pretty_generate(results)
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
