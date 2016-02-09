# goes into the rails root
# based on tests/test_coverage in miq source

# INCLUDE_GLOBS is eager, and tries to get all the rubies
INCLUDE_GLOBS = [
  '../lib/**/*.rb',
  'lib/**/*.rb',
  'app/**/*.rb',
]

# EXCLUDE_GLOBS comes from the test_coverage script. Additionally, it filters
# out things that do stuff when they're evaluated, like the workers and the
# appliance console.
# Models are loaded separately, so they're also excluded here.
EXCLUDE_GLOBS = [
  '../lib/appliance_console*',
  '../lib/coverage_hook*',
  'lib/extensions/**',
  'lib/db_administration/**',
  'lib/miq_automation_engine/**',
  'lib/rubyrep_filters/**',
  'lib/tasks/**',
  'lib/workers/**',
  'app/models/**',
]

# Touch ALL THE THINGS
# Excluding the ruby files in EXCLUDE_GLOBS, require every ruby file in INCLUDE_GLOBS
# Then, go through all the models and constantize them (if possible) to make sure they're touched
def touch_all_the_things
  includes = Dir.glob(INCLUDE_GLOBS)
  excludes = Dir.glob(EXCLUDE_GLOBS)

  includes.each do |file|
    if excludes.include?(file)
      next
    end
    begin
      require File.basename(file, ".rb")
      puts "#{file} touched"
    rescue StandardError, LoadError, MissingSourceFile
      next
    end
  end

  Dir.glob('app/models/**/*.rb').each do |file|
    begin
      model_name = File.basename(file, ".rb").camelize
      model_name.constantize
      puts "#{model_name} loaded"
    rescue StandardError, LoadError, MissingSourceFile
      next
    end
  end
end

touch_all_the_things
