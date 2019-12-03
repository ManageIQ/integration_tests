from textwrap import dedent

import fauxfactory

user_list_hash_data = dedent(
    """
module Demo
  module Automate
    module System
      module Request
        module Test
          class AvailableUsers
            def initialize(handle = $evm)
              @handle = handle
            end

            def main
              fill_dialog_field(fetch_list_data)
            end

            private

            def fetch_list_data
              user1 = {:id => 1, :name => 'Fred', :age => 52, :email => "fred@bedrock.com"}
              user2 = {:id => 2, :name => 'Barney', :age => 55, :email => "barney@bedrock.com" }
              user3 = {:id => 3, :name => 'Wilma', :age => 39, :email => "wilma@berdock.com" }
              user4 = {:id => 4, :name => 'Betty', :age => 38, :email => "betty@bedrock.com" }
              user_list = { user1 => "#{user1[:name]} - ID #{user1[:id]}",
                            user2 => "#{user2[:name]} - ID #{user2[:id]}",
                            user3 => "#{user3[:name]} - ID #{user3[:id]}",
                            user4 => "#{user4[:name]} - ID #{user4[:id]}"}
              @handle.log(:info, "User List #{user_list}")
              return nil => "<none>" if user_list.blank?

              user_list[nil] = "<select>" if user_list.length > 1
              user_list
            end

            def fill_dialog_field(list)
              dialog_field = @handle.object

              # sort_by: value / description / none
              dialog_field["sort_by"] = "description"

              # sort_order: ascending / descending
              dialog_field["sort_order"] = "ascending"

              # data_type: string / integer
              dialog_field["data_type"] = "string"

              # required: true / false
              dialog_field["required"] = "true"

              dialog_field["values"] = list
              dialog_field["default_value"] = list.length == 1 ? list.keys.first : nil
            end
          end
        end
      end
    end
  end
end

if __FILE__ == $PROGRAM_NAME
  Demo::Automate::System::Request::Test::AvailableUsers.new.main
end
        """
)

tag_values = [fauxfactory.gen_alphanumeric(start="tag_", length=12).lower(), "{tag_exist}"]
tag_delete_from_category = (
    f"""
    # Create tag under category - 'Location'
    $evm.execute(
'tag_create', 'location', :name => '{tag_values[0]}', :description => 'Testing tag {tag_values[0]}'
)
    # Check if tag exists
    tag_exist = $evm.execute('tag_exists?', 'location', '{tag_values[0]}')
    $evm.log(:info, "Tag exists: #{tag_values[1]}")

    # Delete the tag
    $evm.execute('tag_delete', 'location', '{tag_values[0]}')

    # Check if deleted tag exists
    tag_exist = $evm.execute('tag_exists?', 'location', '{tag_values[0]}')
    $evm.log(:info, "Tag exists: #{tag_values[1]}")
    """
)

imported_domain_info = {"domain": "testdomain", "namespace": "test", "klass": "TestClass1",
                        "method": "meh", "script": '$evm.log(:info, ":P")'}
