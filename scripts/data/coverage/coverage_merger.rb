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
#           "timestamp": 1518751298
#       }
#   } 
#
# Note coverage data is either:
#
#      - 0: line not covered
#      - > 0: Number of times line covered.
#      - null: Not coverable (e.g. a comment)
#
# 
# The merge file will look like this.
# 
#   {
#       "merged-coverage-data": {
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
#           "timestamp": 1518751298
#       }
#   } 
#
require 'fileutils'
require 'json'
require 'logger'
require 'optparse'
require 'simplecov'
require 'simplecov/result'

rails_root = '/var/www/miq/vmdb'
data_title = 'merged_data'
results = Hash.new
results[data_title] = {
    'coverage' => { },
    'timestamp' => 0,
}
cfme_version = `rpm -q --qf '%{VERSION}' cfme`

# Setup simple logging
$log = Logger.new(STDOUT)
$log.level = Logger::INFO
$log.formatter = proc do |severity, datetime, progname, msg|
  "#{msg}\n"
end

def merge_file(file, coverage_data, merge_data)
  $log.debug("\t#{file}")

  if !merge_data.key?(file)
    $log.debug("\t\tnew file!")
    merge_data[file] = coverage_data
  else
    $log.debug("\t\tfile exist in merge data...merging.")
    merge_source_coverage(merge_data[file], coverage_data)
  end
end

def merge_source_coverage(src_coverage_data1, src_coverage_data2)                                                                  
  # Since this is the coverage data for the same source file
  # even though it is across different processes and/or appliances 
  # we expect the number of lines in the source file to be equal.   
  if src_coverage_data1.length != src_coverage_data2.length
    raise ArgumentError, 'Both files are not the same length!'
  end
  num_of_lines = src_coverage_data1.length

  # We expect lines to be marked with either 0, some positive integer
  # or Null. If both lines are integers (0 included) we just add the two
  # lines together for the result.   If both are Null they stay Null.
  # If there is a mix we raise and exception.  Null denotes a line that
  # would not be counted for code coverage and for it to be Null in one 
  # array and not the other implies actual differences in the files which is
  # not allowed.
  line_number = 0
  while line_number < num_of_lines
    $log.debug("#{line_number}: #{src_coverage_data1[line_number]} #{src_coverage_data2[line_number]}")

    if src_coverage_data1[line_number].is_a?(Fixnum) and src_coverage_data2[line_number].is_a?(Fixnum)
      src_coverage_data1[line_number] += src_coverage_data2[line_number]

    # If both were not numbers, and both are not Null, we need to raise an exception.
    elsif !(src_coverage_data1[line_number].is_a?(NilClass) and src_coverage_data2[line_number].is_a?(NilClass))
      raise ArgumentError, <<EOM
Coverage data should be either Null or a Number!
DATA1: #{src_coverage_data1[line_number]} is #{src_coverage_data1[line_number].class}
DATA2: #{src_coverage_data2[line_number]} is #{src_coverage_data2[line_number].class}
EOM
    end
    
    line_number += 1
  end
end

# Parse command line arguments:
options = {}
options[:coverage_root] = './coverage'
OptionParser.new do |parser|
  parser.on("-c", "--coverageRoot DIR", "Path to the coverage directory.") do |v|
    options[:coverage_root] = v
  end
  parser.on("-v", "--verbose", "Turn on verbose output.") do 
    $log.level = Logger::DEBUG
  end
end.parse!

puts "Scanning for results in #{options[:coverage_root]}"
json_files = Dir.glob(
  File.join(options[:coverage_root], "*", "*", ".resultset.json")
)
merged_dir = File.join(options[:coverage_root], 'merged')
merged_result_set = File.join(merged_dir, '.resultset.json')

skipped_files = Array.new
for json_file in json_files
  begin
    json = File.read(json_file)
    data = JSON.parse(json)

    # Pull the file data out of the coverage hash
    data.each {|key, value|
      $log.info("Processing #{key}...")
      coverage = value['coverage']

      # The structure has to have a timestamp.   
      # So I just arbitrarily grab the same one from the
      # the merge files.   Last one wins.
      results[data_title]['timestamp'] = value['timestamp']

      # Process each file:
      coverage.each {|file, coverage_data|
        merge_file(file, coverage_data, results[data_title]['coverage'])
      }

      # We only expect one key at the top level, so break out.
      break
    }
    
    $log.info("\tMerged #{json_file}")
  rescue JSON::ParserError => e
    $log.error("\tSkipping #{json_file}, no valid JSON")
    $log.error("\t#{e}")
    skipped_files.push(json_file)
  end
end

# Show the skipped files if any where skipped
if skipped_files.length > 0
    $log.error("The following files were skipped:")
    skipped_files.each do |file|
        $log.error("\t#{file}")
    end
end

if results.empty?
  abort "No results found for merging."
else
  puts "All results merged, compiling report: #{merged_result_set}"
end

# Write the merged data out:
FileUtils.mkdir_p(merged_dir)
File.open(merged_result_set, "w") do |f|
  f.puts JSON.pretty_generate(results)
end

####################
# Build our report #
####################
# Set up simplecov to use the merged results, then fire off the formatters
SimpleCov.project_name "CFME #{cfme_version}"
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
    include_file = src.filename =~ /gems\/manageiq-/
  end
  unless include_file
    include_file = src.filename =~ /gems\/cfme-/
  end 
  ! include_file
end

# Set up groups:
SimpleCov.add_group "REST API", "app/controllers/api"
SimpleCov.add_group "Models", "app/models"
SimpleCov.add_group "Automate Engine", "lib/miq_automation_engine"

# Add all the providers into separate groups.  We will discover the
# current set, so that new providers will automatically be detected,
# ones removed go away.
gem_dir = '/opt/rh/cfme-gemset/bundler/gems'
provider_modules = Dir.glob(
  File.join(gem_dir, 'manageiq-providers-*')
)
provider_modules.each do |provider_module|
  provider = /manageiq-providers-([^-]+)/.match(provider_module)[1]
  SimpleCov.add_group "Provider #{provider}" do |src|
    src.filename =~ %r{(manageiq|cfme)-providers-#{provider}}
  end
end

# Generate HTML report
SimpleCov.result.format!
