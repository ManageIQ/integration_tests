# Based on https://gist.github.com/carbonin/410cc56663769c442e5df61938cdade5
require 'yaml'
require 'nokogiri'
require 'openscap'
require 'tempfile'
require 'optimist'

DEFAULT_SSG_XML_PATH = "/usr/share/xml/scap/ssg/content/ssg-rhel7-ds.xml"

class ScapTest
  PROFILE_ID = "xccdf_org.ssgproject.content_profile_linux-admin-scap".freeze

  def initialize(ssg_path)
      @ssg_path = ssg_path
  end

  def run(yaml_file)
    scap_config = YAML.load_file(yaml_file)
    rules = scap_config['rules']
    values = scap_config['values']

    with_ds_file(rules, values) do |ds_path|
      begin
        session = OpenSCAP::Xccdf::Session.new(ds_path)
        session.load
        session.profile = PROFILE_ID
        session.evaluate
        session.export_results(:xccdf_file => "scap-results.xccdf.xml")
      ensure
        session.destroy if session
      end
    end
  end

  def with_ds_file(rules, values)
    Tempfile.create("scap_ds") do |f|
      write_ds_xml(f, profile_xml(PROFILE_ID, rules, values))
      f.close
      yield f.path
    end
  end

  def profile_xml(profile_id, rules, values)
    builder = Nokogiri::XML::Builder.new do |xml|
      xml.Profile(:id => profile_id) do
        xml.title(profile_id)
        xml.description(profile_id)
        rules.each { |r| xml.select(:idref => r, :selected => "true") }
        values.each { |k, v| xml.send("refine-value", :idref => k, :selector => v) }
      end
    end
    builder.doc.root.to_xml
  end

  def write_ds_xml(io, profile_xml)
    File.open(@ssg_path) do |f|
      doc = Nokogiri::XML(f)
      model_xml_element(doc).add_next_sibling("\n#{profile_xml}")
      io.write(doc.root.to_xml)
    end
  end

  def model_xml_element(doc)
    doc.xpath("//ns:model[1]", "ns" => "http://checklists.nist.gov/xccdf/1.2")[0]
  end
end

opts = Optimist::options do
  opt :rulesfile, "The YAML formatted file with the SCAP rules to check", :type => :string, :required => true
  opt :ssg_path, "The SSG path", :type => :string, :required => false, :default => DEFAULT_SSG_XML_PATH
end

Trollop.die "File #{opts[:rulesfile]} does not exist" unless File.exist?(opts[:rulesfile])

ScapTest.new(opts[:ssg_path]).run(opts[:rulesfile])
`oscap xccdf generate report scap-results.xccdf.xml > scap-report.html`

# The rules file should be structured in YAML format as follows:
#rules:
#  - xccdf_org.ssgproject.content_group_sshd_set_idle_timeout
#  - xccdf_org.ssgproject.content_group_sshd_use_approved_ciphers
#values:
#  xccdf_org.ssgproject.content_value_sshd_idle_timeout_value: 15_minutes
