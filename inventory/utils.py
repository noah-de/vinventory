from django.db import models
from inventory.models import VirtualMachine, VMHost, DataStore, Vendor, IpAddress
import sys,os,csv
from django.core.management import call_command

def clearAll():
  ''' Opens a file for reading and returns an open file stream 
      which can be looped over, or stepped through. Each line 
      is a dictionary
      @param model - the model to clear
  '''
  #call_command('reset', 'inventory')
  
  VMHost.objects.all().delete()
  DataStore.objects.all().delete()
  VirtualMachine.objects.all().delete()

def openDataSource(file_path, names):
  ''' Opens a file for reading and returns an open file stream 
      which can be looped over, or stepped through. Each line 
      is a dictionary
      @param file_path - must be a valid absolute path to a readable
        file
      @param names - a tuple of column names
  '''
  # The count is assuming that the first line in the file is the header
  count = len(open(file_path).read().splitlines())
  stream = open(file_path)
  dataReader = csv.DictReader(open(file_path), fieldnames=names)
  
  # Don't need the header, because the names don't match
  # Skipping this line
  dataReader.next()
  return ((count-1), dataReader)

def createDataStores(file_path, names):
  ''' Given the datastream provided by openDataStream(), this method 
      creates datastore objects
  '''
  # Open the datastream and get a line count
  records, datastream = openDataSource(file_path, names)

  i = 0
  for row in datastream:
      print row['name'],
      exists = DataStore.objects.filter(name=row['name'])
      if not exists:
          #"Name","CapacityMB","FreeSpaceMB","FileSystemVersion"
          datastore = DataStore.create(**row)
          
          print '... created'
      else:
          #print row,"...exists",
          exists.update(**row)
          datastore = DataStore.objects.get(name=row['name'])
          print "...updated"
      i += 1
      datastore.save()
  result =(i == records)
  assert result, "record count {0} does not match the count of records processed {1}".format(records,i)
  
def createVirtualHosts(file_path, names):
  ''' Given the datastream provided by openDataStream(), this method 
      creates virtual host objects, linked with their respective 
      hardware manufacturer
  '''
  # Open the datastream and get a line count
  records, datastream = openDataSource(file_path, names)

  i = 0
  # For every line in the file (lines represent Virtual Machine Hosts)
  for row in datastream:
      print row['Manufacturer'],
      
      # Seek an existing vendor (since vendor is a requirement)
      if not Vendor.objects.filter(name=row['Manufacturer']):
          # create vendor
          v  =  Vendor()
          v.name = row['Manufacturer']
          v.save()
          print ' ...created'
      else:
          v  = Vendor.objects.get(name=row['Manufacturer'])
          print ' ...exists'
      
      print row['Name'],
      
      # Seek out an existing Virtual Machine Host
      if not VMHost.objects.filter(name=row['Name']):
          # If it does not exist, create one and specify the name
          vmh      = VMHost()
          vmh.name = row['Name']
          print ' ...created'
      else:
          # If it exists, grab it and assign it to vmh variable
          vmh = VMHost.objects.get(name=row['Name'])
          print ' ...exists'
  
      # We can now update the object and save it
      vmh.manufacturer = v
      vmh.model        = row['Model']
      vmh.cpuCount     = int(row['NumCpu'])
      vmh.cpuTotal     = int(row['CpuTotalMhz'])
      vmh.cpuUsage     = row['CpuUsageMhz']
      vmh.processor    = row['ProcessorType']
      vmh.save()
      i += 1
      print 'updated'
  result =(i == records)
  assert result, "record count {0} does not match the count of records processed {1}".format(records,i)

def createIPs(file_path, names):
  ''' Given the datastream provided by openDataStream(), this method 
      creates IP objects which belong to virtual machines
  '''
  # Open the datastream and get a line count
  records, datastream = openDataSource(file_path, names)

  for row in datastream:
    # Does this virtual machine have an associated IP?
    if row['ip'] != '':
      # Yes, there are IP address entries, proceed to process them
      # Does the associated virual machine exist?
      if VirtualMachine.objects.filter(name=row['vm']):
        # If the virtual machine exists, get it
        vm = VirtualMachine.objects.get(name=row['vm'])
        
    	# What IP addresses are currently associated with this vm? 
    	# values_list returns a tuple, where the ip address is the 2nd item: ips[1]
        ips = vm.ipaddress_set.values_list()
    	
    	#declare an empty set
        existing_ips = set()
    	
        # For each existing ip
        for ip in ips:
            # add the value to the set
            existing_ips.add(ip[1])
    
        # For each IP address in the datafile...
        new_ips = set(row['ip'].split(' '))
    	
        # Compare the sets
        # http://docs.python.org/library/stdtypes.html#set
        # http://docs.python.org/tutorial/datastructures.html#sets
        ips_to_remove = existing_ips - new_ips
        ips_to_add    = new_ips - existing_ips
    	
    	
        # If there are IPs to addfor i in ips_to_add:
        for i in ips_to_add:
          print i,
          ip_exists = IpAddress.objects.filter(address=i)
          if not(ip_exists):
            ip         = IpAddress()
            print ' ...created'
          else:
            ip  = IpAddress.objects.get(address=i)
            print ' ...exists', 
          ip.address = i
          ip.vm      = vm
          ip.save()
          print 'and updated'
    	  
        # If IP addresses have been removed:
        for i in ips_to_remove:
            print i,
            ip_exists = IpAddress.objects.filter(address=i)
            if ip_exists:
                ip  = IpAddress.objects.get(address=i).delete()
                print '... removed',
            else:
                msg = 'IP adress {0} doesn\'t exist!'.format(i)
                raise RuntimeError(msg)
      else:
        msg = 'Virtual Machine {0} doesn\'t exist!'.format(row[0])
        raise RuntimeError(msg)

def createVirtualMachines(file_path, names):
  ''' Given the datastream provided by openDataStream(), this method 
      creates virtual machine objects, which are linked to their 
      respective virtual hosts
  '''
  # Open the datastream and get a line count
  records, datastream = openDataSource(file_path, names)
  i = 0
  for row in datastream:
    vm_exists= VirtualMachine.objects.filter(name=row['Name'])

    # Populate the boolean value for the power state (any sting is True)
    if row['PowerState'].endswith('Off'):
      row['PowerState'] = False
    if not vm_exists:
      # Only proceed if the virtual host exists
      if VMHost.objects.filter(name = row['VMHost']):
          # Create a new virtual machine
          vm      = VirtualMachine()
          vm.name = row['Name']
      else:
          msg = 'Virtual host({0}) does not exist'.format(row['VMHost'])
          # http://docs.python.org/tutorial/errors.html
          raise RuntimeError(msg)

      vm.powerState = row['PowerState']
      vm.cpuCount   = row['NumCpu']
      vm.memoryMB   = row['MemoryMB']
      vm.host       = VMHost.objects.get(name = row['VMHost'])
      vm.save()
      print '({0}) created'.format(row['Name']),
    else:
        # The vitual machine exists, assign it to 'vm'
        print '({0}) already exists'.format(row['Name']),
        vm = VirtualMachine.objects.get(name=row['Name'])

    # The following is performed on existing or newly created VMs
    # Seek out the data store, it's required to save the vm
    for d in row['Datastore'].split(' '):
        ds  = DataStore.objects.get(name = d)
        vm.datastore.add(ds)
        print '  added datastore ({0})'.format(d),

        # Name is the identifier, so we can't update it
        # vm.name       = row['Name']

        vm.powerState = row['PowerState']
        vm.cpuCount   = row['NumCpu']
        vm.memoryMB   = row['MemoryMB']
        vm.notes      = row['Notes']
        vm.host       = VMHost.objects.get(name = row['VMHost'])
    vm.save()
    print 'updated'
    i += 1
  result = (i == records)
  assert result, "record count {0} does not match the count of records processed {1}".format(records,i)    