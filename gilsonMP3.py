# # !/usr/bin/env python3

# -------------------------------------------------------------------
# Basic I/O class for Gilson Minipuls3 peristaltic pump 
# -------------------------------------------------------------------

# Modified from https://github.com/weallen/starmap
# NOTE: Functions within class are organized in alphabetical order

# ----------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------
import serial
import time

# ----------------------------------------------------------------------
# Define important serial characters
# ----------------------------------------------------------------------
acknowledge =  '\x06'
start = '\x0a'
stop = '\x0d'
R = '\xd2' # ASCII R (82 = 0x52) + 128 = 210 = 0xd2 (remote response)
K = '\xcb' # ASCII K (75 = 0x4b) + 128 = 203 = 0xcb (keypad response)

# ----------------------------------------------------------------------
# Gilson Minipuls3 Class Definition
# ----------------------------------------------------------------------
class APump():
	def __init__(self, com_port = 'COM8', verbose = True, parameters = False):
		
		# # Define attributes -- implement this in future versions
		# self.com_port = parameters.get('pump_com_port', 'COM5')
		# self.pump_ID = parameters.get('pump_ID', 30)
		# self.verbose = parameters.get('verbose', True)
		# #self.simulate = parameters.get('simulate_pump', True)
		# self.serial_verbose = parameters.get('serial_verbose', False)
		# self.flip_flow_direction = parameters.get('flip_flow_direction', False)
		
		# Define attributes - for now just hard-code them instead of
		#	parsing XML file
		self.com_port = com_port
		self.pump_ID = 30
		self.verbose = verbose
		# self.flip_flow_direction = False
		self.flip_flow_direction = True		#since useqFISH uses the pump in reverse direction
		self.read_length = 40
		
		# Create serial port
		self.serial = serial.Serial(port = self.com_port,
									baudrate = 19200,
									parity = serial.PARITY_EVEN,
									bytesize = serial.EIGHTBITS,
									stopbits = serial.STOPBITS_TWO,
									timeout = 1) # changed timeout from 0.1
		
		# Define initial pump status
		self.flow_status = 'Stopped'
		self.speed = 0.0
		self.direction = 'Forward'
		
		# self.masterReset()
		self.disconnect()
		self.enableRemoteControl(1)
		self.startFlow(self.speed, self.direction)
		self.confirmRemoteControl()
		self.getStatus()
		print('Initialized Pump')
	
	# ------------------------------------------------------------------
	# Confirm Remote/Keypad Control
	#	NOTE: Original function
	# ------------------------------------------------------------------
	def confirmRemoteControl(self):
		response = self.sendImmediate(self.pump_ID, '?')
		if response == 'R':
			print('Remote control confirmed')
			return True
		elif response == 'K':
			print('Keypad control enabled')
			return False
		else:
			return False
	
	# ------------------------------------------------------------------
	# Close Remote Connection
	# ------------------------------------------------------------------
	def closeRemote(self):
		self.enableRemoteControl(0) # 0 indicates remote is false (so keypad)
			
	# ------------------------------------------------------------------
	# Disconnect from Serial Connection
	# ------------------------------------------------------------------
	def closeSerialPort(self):
		self.serial.close()
	
	# ------------------------------------------------------------------
	# Disconnect
	# ------------------------------------------------------------------
	def disconnect(self):
		self.sendAndAcknowledge('\xff')
	
	# ------------------------------------------------------------------
	# Enable Remote Control
	# ------------------------------------------------------------------
	def enableRemoteControl(self, remote):
		if remote:
			self.sendBuffered(self.pump_ID, 'SR')
		else:
			self.sendBuffered(self.pump_ID, 'SK')
	
	# ------------------------------------------------------------------
	# Get Entire Response - Read all bits in buffer, clear buffer, etc.
	# ------------------------------------------------------------------
	def getEntireResponse(self):
		return self.serial.read(self.read_length)
			
	# ------------------------------------------------------------------
	# Identify Module
	# ------------------------------------------------------------------
	def getIdentification(self):
		return self.sendImmediate(self.pump_ID, '%')
	
	# ------------------------------------------------------------------
	# Get Single Response (Read one bit of buffer)
	# ------------------------------------------------------------------
	def getResponse(self):
		return self.serial.read()
		# # return self.serial.read().decode()
	
	# ------------------------------------------------------------------
	# Get Pump Operation Status
	# ------------------------------------------------------------------
	def getStatus(self):
		message = self.readDisplay()
		print(message)
		
		if self.flip_flow_direction:
			direction = {' ' : 'Not Running',
						 '-' : 'Forward',
						 '+' : 'Reverse'}.get(message[0], 'Unknown')
		else:
			direction = {' ' : 'Not Running',
						 '+' : 'Forward',
						 '-' : 'Reverse'}.get(message[0], 'Unknown')
		
		status = 'Stopped' if direction == 'Not Running' else 'Flowing'
		
		control = {'K' : 'Keypad',
				   'R' : 'Remote'}.get(message[-1], 'Unknown')
				#    'R' : 'Remote'}.get(message[-2], 'Unknown')
		
		auto_start = 'Disabled'
		
		speed = float(message[1:len(message) - 2])
		
		return (status, speed, direction, control, auto_start, 'No Error')
		
	# ------------------------------------------------------------------
	# Master Reset
	# ------------------------------------------------------------------
	def masterReset(self):
		return self.sendImmediate(self.pump_ID, '$')

	# ------------------------------------------------------------------
	# Read Display
	# ------------------------------------------------------------------
	def readDisplay(self):
		return self.sendImmediate(self.pump_ID, 'R')
		
		# Response format: "cs" where
		#	"c" is the code of the last key pressed:
		#		"<" = backwards (CCW)
		#		">" = forwards (CW)
		#		"+" = faster
		#		"-" = slower
		#		"H" = stop
		#		"&" = rabbit (auto to speed 4800)
		#	"s" is the key's status:
		#		"!" if the key was pressed after the last request
		#		"-" if the key remains pressed after the last request
		#		" " a space means that no key was pressed
		# Default response: "$"
	
	# ------------------------------------------------------------------
	# Select Unit
	#
	#	Note: Default unit number (address) is 30
	#	This may need some troubleshooting to take into account
	#		additional possible responses. Still seeing failure sometimes
	#		and not sure why.
	# ------------------------------------------------------------------
	def selectUnit(self, unitNumber):
		devSelect = chr(0x80 | unitNumber) # unitNumber + 128 --> char
			# again, not sure why we need to add 128
		self.sendString(devSelect)
		
		response = self.getEntireResponse()
		response = response.decode('ISO-8859-1') # decode response
			# for some reason UTF-8 doesn't work...
		
		if len(response) == 1: # if response is only repeat of devSelect
			return response == devSelect
		
		elif len(response) > 1:
			if devSelect in response: # if devSelect is in response
				return response[-1] == devSelect #returns true if
					# devSelect is repeated at end of message
		
		else:
		#print('Unit selection failed')
			return False
	
	# ------------------------------------------------------------------
	# Send and Acknowledge
	# ------------------------------------------------------------------
	def sendAndAcknowledge(self, string):
		for i in range(0, len(string)):
			self.sendString(string[i])
			self.getResponse()
	
	# ------------------------------------------------------------------
	# Send Buffered Command
	#
	#	Buffered commands send instructions to the instrument and are
	#		executed one at a time.
	#	Note: Response to buffered command is a period (.)
	# ------------------------------------------------------------------
	def sendBuffered(self, unitNumber, command):
		while not self.selectUnit(unitNumber):
			time.sleep(1)
			self.selectUnit(unitNumber)		
		self.sendAndAcknowledge(start + command + stop)
		self.disconnect()
		
	# ------------------------------------------------------------------
	# Send Immediate Command
	#
	#	Immediate commands request status information from the
	#		instrument and are executed immediately, temporarily
	#		interrupting other commands in progress.
	# ------------------------------------------------------------------
	def sendImmediate(self, unitNumber, command):
		while not self.selectUnit(unitNumber):
			time.sleep(1)
			self.selectUnit(unitNumber)
		self.sendString(command[0])
		newCharacter = self.getResponse() # read one bit
		response = ''
		
		if len(newCharacter) > 0:
			while not (ord(newCharacter) & 0x80):
				response += newCharacter.decode('ISO-8859-1')
				self.sendString(acknowledge)
				newCharacter = self.getResponse()
			response += chr(ord(newCharacter.decode('ISO-8859-1')) & ~0x80)
		
		self.disconnect()
		
		return response
	
	# ------------------------------------------------------------------
	# Send String
	# ------------------------------------------------------------------
	def sendString(self, string):
		self.serial.write(string.encode())
					
	# ------------------------------------------------------------------
	# Set Flow Direction
	# ------------------------------------------------------------------
	def setFlowDirection(self, forward):
		if self.flip_flow_direction:
			if forward:
				self.sendBuffered(self.pump_ID, 'K<')
			else:
				self.sendBuffered(self.pump_ID, 'K>')
		else:
			if forward:
				self.sendBuffered(self.pump_ID, 'K>')
			else:
				self.sendBuffered(self.pump_ID, 'K<')
	
	# ------------------------------------------------------------------
	# Set Pump Speed
	# ------------------------------------------------------------------
	def setSpeed(self, rotation_speed):
		if rotation_speed >= 0 and rotation_speed <= 48:
			rotation_int = int(rotation_speed * 100)
			self.sendBuffered(self.pump_ID, 'R' + ('%04d' % rotation_int))
			
			# NOTE:
			# '%04d' % rotation_int --> ensures input to Minipuls3
			#	is in the correct format (4 places, integer)
			#	e.g. rotation_speed = 12.4321
			#		then rotation_int = 1243
			#		and '%04d' % rotation_int --> 1243
			#	BUT if rotation_speed = 5
			#		then rotation_int = 500
			#		and '%04d' % rotation_int --> 0500
	
	# ------------------------------------------------------------------
	# Start Pump Flow
	# ------------------------------------------------------------------
	def startFlow(self, speed, direction = 'Forward'):
		self.setSpeed(speed)
		# self.speed = speed
		self.setFlowDirection(direction == 'Forward')
	
	# ------------------------------------------------------------------
	# Stop Pump Flow
	# ------------------------------------------------------------------
	def stopFlow(self):
		self.sendBuffered(self.pump_ID, 'KH')
		return True
	
		# Changed from original, which just set speed to 0
						
# -----------------------------------------------------------------------
# Test/Demo of Class
# -----------------------------------------------------------------------

if (__name__ == '__main__'):
	
	pump = APump()
	print('Pump Initialized')
	pump.readDisplay()
	
	if pump.confirmRemoteControl():
		response = input('Start flow? Y/N ')
		if response == 'Y' or response == 'y':
			pump.startFlow(speed = 20, direction = 'Forward')
			print('Flow started')
	
			pause_time = 10
	
			time.sleep(pause_time)
	
			pump.stopFlow()
			print('Flow stopped')
	
	pump.disconnect()
	print('Pump disconnected')
		
