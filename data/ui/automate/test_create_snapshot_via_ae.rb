###################################
#
# EVM Automate Method: createSnapshot
#
# Notes: This method creates a snapshot on a given VM via web service API
#
# Inputs: GUID, [snap_name, snap_description]
#
###################################
begin
  @method = 'createSnapshot'
  $evm.log("info", "#{@method} - EVM Automate Method Started")

  # Turn of verbose logging
  @debug = true

  ####################
  #
  # Method: createSnapshot
  #
  ####################
  def createSnapshot(vm, snap_name, snap_desc=snap_name)
    $evm.log("info","#{@method} - VM:<#{vm.name}> Creating Snapshot:<#{snap_name}> Description:<#{snap_desc}>")
    vm.create_snapshot(snap_name, snap_desc)
  end

  #$evm.root.attributes.sort.each { |k, v| $evm.log("info", "\t#{k}: #{v}")} if @debug

  # Get VM object from the root object
  vm = $evm.root['vm']

  # If VM is nil then assume web service call and look for GUID from root object
  if vm.nil?
    $evm.log("info","Execution of method:<#{@method}> via API detected") if @debug
    # Get GUID from foot object
    guid = $evm.root['guid']

    # Lookup VM by GUID
    vm = $evm.vmdb('vm').find_by_guid(guid)
    # Bail out if VM is not found
    raise "#{@method} - VM with GUID:<#{guid}> not found" if vm.nil?
    $evm.log("info","#{@method} - Assigning VM:<#{vm.name}> to root object") if @debug
    $evm.root['vm'] = vm
    $evm.log("info","#{@method} - Found VM:<#{vm.name}> via GUID:<#{guid}>") if @debug
  end

  snap_name = $evm.root['snap_name'] || "Snapshot #{Time.now}"
  snap_desc = $evm.root['snap_desc'] || "Snapshot:<#{snap_name}> for #{vm.name}"

  # Call createSnapshot method
  createSnapshot(vm, snap_name, snap_desc)

  #
  # Exit method
  #
  $evm.log("info", "#{@method} - EVM Automate Method Ended")
  exit MIQ_OK


  #
  # Set Ruby rescue behavior
  #
rescue => err
  $evm.log("error", "#{@method} - [#{err}]\n#{err.backtrace.join("\n")}")
  exit MIQ_ABORT
end