# goes into the rails root

require 'json'
require 'simplecov'
require 'simplecov-rcov'

# After merging, we want the html report as well as the rcov report for jenkins
class MergedFormatter
  def format(result)
     SimpleCov::Formatter::HTMLFormatter.new.format(result)
     SimpleCov::Formatter::RcovFormatter.new.format(result)
  end
end

results = Hash.new
coverage_root = File.join(File.expand_path(Rails.root), "coverage")
json_files = Dir.glob(
  File.join(coverage_root, "*/.resultset.json")
)

for json_file in json_files
  begin
    json = File.read(json_file)
    results.update(JSON.parse(json))
  rescue JSON::ParserError
    # Don't know/care why simplecov didn't write valid json
  ensure
    FileUtils.rm_rf(File.dirname(json_file))
  end
end

JSON.dump(
  results, File.new(File.join(coverage_root, ".resultset.json"), "w")
)

# After merging, switch the coverage root and let simplecov's exit hook
# generate the report
SimpleCov.coverage_dir coverage_root
SimpleCov.formatter = MergedFormatter
