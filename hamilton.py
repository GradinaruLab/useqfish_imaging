# # !/usr/bin/env python3

# -------------------------------------------------------------------
# A basic class for serial interface with a series of daisy chained 
#	Hamilton MVP valve controllers
# -------------------------------------------------------------------

# Modified from https://github.com/weallen/starmap
# NOTE: Functions within class are organized in alphabetical order

# -------------------------------------------------------------------
# Import
# -------------------------------------------------------------------
import sys
import time

# -------------------------------------------------------------------
# Hamilton MVP Class Definition
# -------------------------------------------------------------------

class HamiltonMVP():
	
	def __init__(self, com_port = 'COM11', verbose = False):
		
		# Define attributes
		self.com_port = com_port
		self.verbose = verbose
		
		# Create serial port
		import serial # why is this imported here?
		self.serial = serial.Serial(port = self.com_port,
									baudrate = 9600,
									parity = serial.PARITY_ODD,
									bytesize = serial.SEVENBITS,
									stopbits = serial.STOPBITS_ONE,
									timeout = 1)
		
		# Define important serial characters:
		self.acknowledge = '\x06'
		# self.carriage_return = '\x13'
		self.carriage_return = '\r'
		# self.negative_acknowledge = '\x15'
		self.negative_acknowledge = '\x21'
		self.read_length = 64
		self.char_offset = 97 # offset to convert int current_devices
			# to ascii addresses )(0 = a, 1 = b, etc.)
		
		# Define/initialize valve and port properties
		# self.max_valves = 16
		self.max_valves = 2 # we only will have 3 valves, so try to
			# eliminate confusion (and save time initializing) by
			# setting max valves to 3 instead of entire capacity of 16
		self.valve_names = []
		self.num_valves = 0
		self.valve_configs = []
		self.max_ports_per_valve = [8, 8]
		self.current_port = []
		
		# Configure device
		self.autoAddress()
		self.autoDetectValves()
		
	# -------------------------------------------------------------------
	# Define Device Addresses (Auto-Address):
	#	Must be first command issued
	# -------------------------------------------------------------------
	def autoAddress(self):
		auto_address_cmd = '1a\r'
		if self.verbose:
			print('Addressing Hamilton Valves')
		self.writeToSerialPort(auto_address_cmd)
		self.readSerialPort() # clear buffer

		
	
	# -------------------------------------------------------------------
	# Auto Detect and Configure Valves:
	# -------------------------------------------------------------------
	def autoDetectValves(self):
		
		if self.verbose:
			print('Opening the Hamilton MVP Valve Daisy Chain')
			print('   ' + 'Com Port: ' + str(self.com_port))
		
		for valve_ID in range(self.max_valves): # loop over all possible valves
			
			# Generate address character (0 = a, 1 = b, etc.)
			device_address_character = chr(valve_ID + self.char_offset)
			
			# Populate "valve_names" with potential valve names (ascii)
			self.valve_names.append(device_address_character)
			
			# Attempt to initialize valve:
			found_valve = self.initializeValve(valve_ID)
			# found_valve = ('Acknoledge', True, '\x06\r')
			
			if found_valve[1]: # if initialization completed successfully
				valve_config = self.howIsValveConfigured(valve_ID)
				print(f"valve_config: {valve_config}")
				if valve_config[1]: # successful response
					self.valve_configs.append(valve_config[0]) # CHECK
					self.max_ports_per_valve.append(self.numPortsPerConfiguration(valve_config[0])) # CHECK
					self.current_port.append(valve_config[0]) # CHECK
					
					if self.verbose:
						print('Found ' + valve_config[0] + ' device at valve_id ' +
							str(valve_ID))
				
			else:
				if self.verbose:
					print('not found_valve[1] -- not successful initizliation')
					print('found_valve output: ' + str(found_valve))
				break

		# Set number of valves of current configuration
		self.num_valves = len(self.valve_configs)
		if self.verbose:
			print('Number of valves: ' + str(self.num_valves))
		
		# If no valves detected:
		if self.num_valves == 0:
			self.valve_names = '0'
			print('Error: no valves discovered')
			return False # return failure
		
		# Display found values
		print('Found ' + str(self.num_valves) + ' Hamilton MVP Valves')
		for valve_ID in range(self.num_valves):
			print('   ' + 'Device ' + self.valve_names[valve_ID] + 
				' is configured with ' + self.valve_configs[valve_ID])
		
		self.waitUntilNotMoving(self.num_valves-1)
		
		print('Initialized Valves')
		
		return True	
	
	# -------------------------------------------------------------------
	# Change Port Position
	# -------------------------------------------------------------------
	def changePort(self, valve_ID, port_ID, direction = 0, wait_until_done = True):

		print(f">>> changing {valve_ID} valve's port to {port_ID}")
		
		# Check validity of valve and port IDs
		if not self.isValidValve(valve_ID):
			if self.verbose:
				print('changePort - isValidValve failed for port ' + str(port_ID))
			return False
		if not self.isValidPort(valve_ID, port_ID):
			if self.verbose:
				print('changePort - isValidPort failed for port ' + str(port_ID))
			return False
		
		# Compose message and increment port_ID (starts at 1)
		message = 'LP' + str(direction) + str(port_ID) + 'R\r'
		
		# Get response - acknowledge/negative acknowledge
		response = self.inquireAndRespond(valve_ID, message)
		
		if response[0] == 'Negative Acknowledge':
			print('Move failed: ' + str(response))
		
		if response[1]: # Acknowledged move
			self.current_port[valve_ID] = port_ID		
		
		if wait_until_done:
			self.waitUntilNotMoving(valve_ID, pause_time = 1)
		
		print(f">>> {valve_ID} valve's port is moved to {port_ID}")
		return response[1] # Should be True
	
	# -------------------------------------------------------------------
	# Check Valve Setup
	# 	Double-check valves are set up correctly
	# 	NOTE: Only configured for STARmap, need to broaden functionality eventually
	# -------------------------------------------------------------------
	def checkValveSetup(self):
		# portNames = self.getPortNames('STARmap')
		valveA = portNames[0]
		valveB = portNames[1]
	
		# Check Valve A
		for i in range(len(valveA)):
			print('\nValve A, Port #%d' % (i+1) + ' = ' + valveA[i])
			response = input('    Is this correct? Y/N: ')
			if response == 'Y' or response == 'y':
				i += 1
			else:
				print('\nResponse not recognized. Check valve and try again.')
				print('\nValve A, Port #%d' % (i+1) + ' = ' + valveA[i])
				response = input('    Is this correct? Y/N: ')
		print('\nValve A checked successfully!')
		valveA_check = True
	
		# Check Valve B
		for i in range(len(valveB)):
			print('\nValve B, Port #%d' % (i+1) + ' = ' + valveA[i])
			response = input('    Is this correct? Y/N: ')
			if response == 'Y' or response == 'y':
				i += 1
			else:
				print('\nResponse not recognized. Check valve and try again.')
				print('\nValve B, Port #%d' % (i+1) + ' = ' + valveA[i])
				response = input('    Is this correct? Y/N: ')
		print('\nValve B checked successfully!')
		valveB_check = True
		
		# return (valveA_check, valveB_check)
	
	# -------------------------------------------------------------------
	# Close Serial Port
	# -------------------------------------------------------------------
	def closeSerialPort(self):
		self.serial.close()
		if self.verbose:
			print('Closed Hamilton Valves')
		
	# -------------------------------------------------------------------
	# Generate Default Port Names
	#	NOTE: Not called in any other HamiltonMVP class functions
	#	NOTE: Consider using this in in next iteration of STARmap code
	# -------------------------------------------------------------------
	def getDefaultPortNames(self, valve_ID):
		
		# Check if valve is valid
		if not self.isValidValve(valve_ID):
			return ('')
		
		# Generate port names
		default_names = []
		for port_ID in range(self.max_ports_per_valve[valve_ID]):
			default_names.append('Port ' + str(port_ID + 1))
		return default_names
	
	# -------------------------------------------------------------------
	# Generate Rotation Direction Labels
	#	NOTE: Not called in any other HamiltonMVP class functions
	# -------------------------------------------------------------------
	def getRotationDirections(self, valve_ID):
		
		# Check if valve is valid:
		if not self.isValidValve(valve_ID):
			return ('')
		
		# Generate labels: 0 = clockwise, 1 = counter-clockwise
		return ('Clockwise', 'Counter Clockwise')
	
	# -------------------------------------------------------------------
	# Get Valve Staus
	#	NOTE: Modified from original
	# -------------------------------------------------------------------
	def getStatus(self, valve_ID):
		valveLocation = self.whereIsValve(valve_ID)
		doneMoving = self.isMovementFinished(valve_ID)
		overloadStatus = self.isValveOverloaded(valve_ID)
		if self.verbose:
			print('Valve location: ' + str(valveLocation))
			print('Done moving? ' + str(doneMoving))
			print('Is valve overloaded? ' + str(overloadStatus))
		return (valveLocation[0], doneMoving[0], overloadStatus[0])
		# original code:
		# return (self.whereIsValve(valve_ID), not self.isMovementFinished(valve_(D))
		
		# This returns:
		# (port number int 0-7, done moving? bool, valve overloaded? bool)
	
	# -------------------------------------------------------------------
	# Check Valve Configuration
	# -------------------------------------------------------------------
	def howIsValveConfigured(self, valve_ID):
		response = self.inquireAndRespond(valve_ID,
								message = 'LQT\r',
								dictionary = {'2' : '8 ports',
											  '3' : '6 ports',
											  '4' : '3 ports',
											  '5' : '2 ports @180',
											  '6' : '2 ports @90',
											  '7' : '4 ports'},
								default = 'Unknown response')
		return response
		# response format: ('8 ports', True, messageTo_inquireAndRespond)
			# original code returned response[0] but that makes no sense
		
	# -------------------------------------------------------------------
	# Determine Number of Active Valves
	#	NOTE: Not called in any other HamiltonMVP class functions
	# -------------------------------------------------------------------
	def howManyValves(self):
		return self.num_valves
	
	# -------------------------------------------------------------------
	# Initialize Port Position of Given Valve
	# -------------------------------------------------------------------
	def initializeValve(self, valve_ID):
		response = self.inquireAndRespond(valve_ID,
								message = 'LXR\r',
								dictionary = {},
								default = '')
			# response format: ('Acknowledge', True, messageTo_inquireAndRespond)
		return response

	# -------------------------------------------------------------------
	# Basic I/O with Serial Port
	#	This function returns a response tuple used by this class
	#	(dictionary entry, affirmative response?, raw response string)
	# -------------------------------------------------------------------
	def inquireAndRespond(self, valve_ID, message, dictionary={}, default="unknown"):
		
		# Check if the valve_ID valve is initialized:
		if not self.isValidValve(valve_ID):
			print ('isValidValve check failed on valve ' + str(valve_ID))
			return ('', False, '')
		
		# Prepend address of provided valve (0 = a, 1 = b, etc.)
		message = self.valve_names[valve_ID] + message
		
		# Write message and read response
		self.writeToSerialPort(message)
		response = self.readSerialPort()
						
		# Parse response into sent message and response
		# messageStart = response.find(message)
		# messageStop = messageStart + len(message)
		# messageRepeat = response[messageStart:messageStop]
		
		# Parse out actual response from valve, without final carriage return
		responseStart = response[0]
		actualResponse = response[1:-1]
		# print(ascii(actualResponse))

		return_tuple = ["Acknowledge", True]

		if responseStart == self.acknowledge:
			return_value = dictionary.get(actualResponse, default)
			if default:
				if return_value == default:
					return_tuple[0] = default
					return_tuple[1] = False
				# elif return_value:
				else:
					return_tuple[0] = return_value

		if responseStart == self.negative_acknowledge:
			return_tuple[0] = "Negative Acknowledge"
			return_tuple[1] = False

		return (return_tuple[0], return_tuple[1], response)

		# # Check for Negative Acknowledge:
		# if responseStart == self.negative_acknowledge:
		# 	if self.verbose:
		# 		print('"Negative Acknowledge", False, ' + response)
		# 	return ('Negative Acknowledge', False, response)
		
		# # Check for Acknowledge (alone)
		# if responseStart == self.acknowledge:
		# 	# return ('Acknowledge', True, response)
		# 	return_value = dictionary.get(actualResponse, default)
		# 	if self.verbose:
		# 		print('Response from inquireAndRespond = ' + str(return_value))
		# 	if return_value == default:
		# 		return (default, False, response)
		# 	else:
		# 		return (return_value, True, response)
		
	# -------------------------------------------------------------------
	# Poll Movement of Valve
	# -------------------------------------------------------------------
	def isMovementFinished(self, valve_ID):
		response = self.inquireAndRespond(valve_ID,
								message = 'F\r',
								dictionary = {'*' : False,
											  'N' : False,
											  'Y' : True},
								default = 'Unknown response')
		return response
		
	# -------------------------------------------------------------------
	# Check if Port is Valid
	# -------------------------------------------------------------------
	def isValidPort(self, valve_ID, port_ID):
		if not self.isValidValve(valve_ID): # first check if valve is valid
			if self.verbose:
				print('Valve ' + str(valve_ID) + ' is not a valid valve. Port ' +
					str(port_ID) + 'cannot be found')
			return False
		elif not (port_ID <= self.max_ports_per_valve[valve_ID]): # changed < to <=
			if self.verbose:
				print(str(port_ID) + ' is not a valid port on valve ' + 
					str(valve_ID))
			return False
		else:
			if self.verbose:
				print('Port ' + str(port_ID) + ' on valve ' + str(valve_ID) + 
					' is a valid port')
			return True
		
	# -------------------------------------------------------------------
	# Check if Valve is Valid
	# -------------------------------------------------------------------
	def isValidValve(self, valve_ID):
		if not (valve_ID < self.max_valves):
			if self.verbose:
				print(str(valve_ID) + ' is not a valid valve')
			return False
		else:
			if self.verbose:
				print(str(valve_ID) + ' is a valid valve')
			return True
	
	# -------------------------------------------------------------------
	# Poll Overload Status of Valve
	#	NOTE: Not called in any other HamiltonMVP class functions
	# -------------------------------------------------------------------
	def isValveOverloaded(self, valve_ID):
		return self.inquireAndRespond(valve_ID,
							message = 'G\r',
							dictionary = {'*' : False,
										  'N' : False,
										  'Y' : True},
							default = 'Unknown response')
		# if overloaded: (True, True, messageTo_inquireAndRespond)
	
	# -------------------------------------------------------------------
	# Convert Port Configuration String to Number of Ports
	#	e.g. '8 ports' --> 8 (output from howIsValveConfigured)
	# -------------------------------------------------------------------
	def numPortsPerConfiguration(self, configuration_string):
		return {'8 ports' : 8,
				'6 ports' : 6,
				'3 ports' : 3,
				'2 ports @180' : 2,
				'2 ports @90' : 2,
				'4 ports' : 4}.get(configuration_string)
		
	# -------------------------------------------------------------------
	# Read from Serial Port
	# -------------------------------------------------------------------
	def readSerialPort(self):
		response = self.serial.read(self.read_length)
		response = response.decode()
		if self.verbose:
			# print('Received response: ' + str(response))
			print(f'Received response: {ascii(response)}')
		return response
	
	# -------------------------------------------------------------------
	# Reset Chain: Readdress and redetect valves
	#	NOTE: Not called in any other HamiltonMVP class functions
	# -------------------------------------------------------------------
	def resetChain(self):
		
		# Reset device configuration:
		self.valve_names = []
		self.num_valves = 0
		self.valve_configs = []
		self.max_ports_per_valve = []
		
		# Configure device
		self.autoAddress()
		self.autoDetectValves()
	
	# -------------------------------------------------------------------
	# Halt Hamilton Class Until Movement is Finished
	# -------------------------------------------------------------------
	def waitUntilNotMoving(self, valve_ID, pause_time = 1):
		doneMoving = False
		while not doneMoving:
			moveStatus = self.isMovementFinished(valve_ID)
			doneMoving = moveStatus[0] # will be "True" if stopped
			time.sleep(pause_time)
												
	# -------------------------------------------------------------------
	# Poll Valve Configuration
	#	NOTE: Not called in any other HamiltonMVP class functions
	# -------------------------------------------------------------------
	def whatIsValveConfiguration(self, valve_ID):
		if not self.isValidValve(valve_ID): # check if valve is valid
			return ''
		else:
			return self.valve_configs[valve_ID]
			
	# -------------------------------------------------------------------
	# Poll Valve Location
	#	(Modified from original)
	# -------------------------------------------------------------------
	def whereIsValve(self, valve_ID):
		response = self.inquireAndRespond(valve_ID,
								message = 'LQP\r',
								dictionary = {'1' : 0, # was : 'Port 1' (etc.)
											  '2' : 1, 
											  '3' : 2, 
											  '4' : 3, 
											  '5' : 4, 
											  '6' : 5,
											  '7' : 6, 
											  '8' : 7},
								default = 'Unknown Port')
		return response
			# returns, e.g. (0, True, messageTo_inquireAndRespond)
							
	# -------------------------------------------------------------------
	# Write to Serial Port
	# -------------------------------------------------------------------
	def writeToSerialPort(self, message):
		self.serial.write(message.encode())
		# print(message.encode())
		if self.verbose:
			print('Wrote: ' + message) # display all but final CR
	
# -----------------------------------------------------------------------
# Test/Demo of Class
# -----------------------------------------------------------------------

if __name__ == '__main__':
	
	hamilton = HamiltonMVP(com_port = 'COM5', verbose = True)
	# for valve_ID in ra ' + str(valve_ID + 1)
		# text = hamilton.howIsValveConfigured(valve_ID)
		# #text = ' is configured with ' + hamilton.howIsValveConfigured(valve_ID))
		# print(test + ' is configured with ' + text[0])
	
	response = input('Would you like to verify valve setup before running experiment? Y/N: ')
	if response == 'Y' or response == 'y':
		hamilton.checkValveSetup()
	
	# Test changing ports
	print('Changing Port on Valve A to Port #7')
	hamilton.changePort(valve_ID = 0, port_ID = 6)
	print('Changing Port on Valve B to Port #8')
	hamilton.changePort(valve_ID = 1, port_ID = 7)	
	
	valveA_status = hamilton.getStatus(valve_ID = 0)
	print(valveA_status)
	
	valveB_status = hamilton.getStatus(valve_ID = 1)
	print(valveB_status)
	
	hamilton.closeSerialPort()
	
	
	
	
	
	
	
	
	
	
	
	
	
	
		
