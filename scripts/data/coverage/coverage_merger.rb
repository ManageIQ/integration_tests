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
# Additionally it will add any files that did not get covered at all to the resultset file.
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

def add_non_covered_files(resultset, show_added_files)
  # Scan the appliance sources and find files that are not
  # in the resultset, and add them to the resultset.
  $log.info('Adding non-covered files...')

  # Note that we are not including manageiq- gems, and that is because
  # though we pick up some files in the resultset from them mostly we
  # end up using cfme-* gems mostly.   Because of this just picking up
  # all the manageiq- gems' puts the coverage statistics way out of kilter.
  include_globs = [
    '/var/www/miq/vmdb/lib/**/*.rb',
    '/var/www/miq/vmdb/app/**/*.rb',
    '/opt/rh/cfme-gemset/bundler/gems/cfme-*/app/**/*.rb',
  ]

  # The things we are excluding where inherited from the thing_toucher.rb.
  # I'm not really sure why they are excluded.
  exclude_globs = [
    '/var/www/miq/vmdb/lib/coverage_hook*',
    '/var/www/miq/vmdb/lib/extensions/**/*.rb',
    '/var/www/miq/vmdb/lib/tasks/**',
    '/var/www/miq/vmdb/lib/workers/**',
    '/var/www/miq/vmdb/app/models/**/*.rb',
    '/opt/rh/cfme-gemset/bundler/gems/manageiq-*/app/models/**/*.rb',
    '/opt/rh/cfme-gemset/bundler/gems/cfme-*/app/models/**/*.rb',
  ]

  # Go through the source files and if they are not in the
  # resultset and not in the excluded files list, add them
  # to the resultset.
  includes = Dir.glob(include_globs)
  excludes = Dir.glob(exclude_globs)
  added_files = 0
  includes.each do |filename|
    $log.debug("Processing #{filename}")
    if resultset['merged_data']['coverage'].has_key?(filename)
      $log.debug('    Excluded(has coverage)')
      next
    end
    if excludes.include?(filename)
      $log.debug('    Excluded.')
      next
    end

    # We don't have coverage data for this file and it hasn't been
    # excluded so let's create it.   Note we use SimpleCov's LineClassifier
    # to generate the coverage data.  This way we will be in complete
    # agreement with what SimpleCov thinks is a runnable line or not.
    $log.debug('    Generating coverage data.')
    $log.info("Added #{filename}") if show_added_files
    added_files += 1
    lines = IO.readlines(filename)
    classifier = SimpleCov::LinesClassifier.new()
    coverage = classifier.classify(lines)
    resultset['merged_data']['coverage'][filename] = coverage
  end
  $log.info("Added #{added_files} files.")
end

# Parse command line arguments:
options = {}
options[:coverage_root] = './coverage'
options[:ignore_non_covered] = 0
options[:show_added_files] = 0
OptionParser.new do |parser|
  parser.on("-c", "--coverage-root DIR", "Path to the coverage directory.") do |v|
    options[:coverage_root] = v
  end
  parser.on("-v", "--verbose", "Turn on verbose output.") do
    $log.level = Logger::DEBUG
  end
  parser.on("--ignore-non-covered", "Ignore non-covered files.") do
    options[:ignore_non_covered] = 1
  end
  parser.on("--show-added-files", "Show added files due to 0% coverage.") do
    options[:show_added_files] = 1
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

# Add non covered source files to results:
if options[:ignore_non_covered] == 0
  add_non_covered_files(results, options[:show_added_files])
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
# Note we need to setup the filters before we instantiate SimpleCov's
# result from our results hash, as in new versions (e.g. 0.16.1)
# the filtering is applied at the time you instantiate from a hash.
$log.info('Generating HTML report.')
SimpleCov.project_name "CFME #{cfme_version}"
SimpleCov.root '/'
SimpleCov.coverage_dir merged_dir
SimpleCov.formatters = SimpleCov::Formatter::HTMLFormatter
# At this time we don't need the merging facility because how the
# merge above worked (i.e. it's already merged)
SimpleCov.use_merging false

# Clear the original filters and add our own.
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

# Load our result data up:
SimpleCov.instance_variable_set("@result", SimpleCov::Result.from_hash(results))

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
