# !/usr/bin/env python3

# ----------------------------------------------------------------------
# Main program for running STARmap fluidics and imaging -- run this code!
# ----------------------------------------------------------------------

# Work in progress... will be GUIfied eventually...

# NOTE: Timeout set to 1 on both pump and MVPchain because kept timing
#	out for me when I set it lower. Set the timeout experimentally
#	(code would run more smoothly if timeout is decreased)

# ----------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------

import sys
import time
import fusionrest
from gilsonMP3 import APump # Import pump class
from hamilton import HamiltonMVP # Import MVP valve chain class

import os
# To do: import XML with protocol/experiment/setup settings so it's not
#	hard-coded into the pump and MVP class (e.g. COM port)

# ----------------------------------------------------------------------
# Define variables
# ----------------------------------------------------------------------

# speed = 35 # corresponds to approx. 0.5 mL/min given current tubing - starmap

# for useqfish, 1ml required for each round
speed = 20	
time_pumping = [38, 48, 18] # [valve_0_time, valve_1_time, flush_time] for 500 ul
# speed = 30
# time_pumping = 40

# Identifies valve/port configurations for each reagent
# Dictionary: 'Reagent Name' : [valveA_port, valveB_port]
# FluidicsSetup = {'Stripping Buffer' : [0, 6],
# 				 'PBST' : [1, 6],
# 				 'Wash/Imaging Buffer' : [2, 6],
# 				 'Nuclear Stain' : [3, 6],
# 				 'PBS' : [4, 6],
# 				 'Nissl' : [5, 6],
# 				 'Stop Valve' : [6, 6],
# 				 'Cycle 1' : [6, 0],
# 				 'Cycle 2' : [6, 1],
# 				 'Cycle 3' : [6, 2],
# 				 'Cycle 4' : [6, 3],
# 				 'Cycle 5' : [6, 4],
# 				 'Cycle 6' : [6, 5]}

# # Pumping specs: 'Reagent Name' : [time pump on, pause time, repeats]
# 	# Time to leave pump on for each reagent, pause time in seconds, # of repeats
# PumpingSpecs = {'Stripping Buffer' : [240, 600, 2],
# 			 #'PBST' : [?, 300, 3], # n/a, depends on step
#  			 'Wash/Imaging Buffer' : [240, 600, 2],
#  			 'Nuclear Stain' : [240, 1800, 1],
#  			 # 'PBS' : [], # n/a, depends on step
#  			 'Nissl' : [240, 1200, 1],
# 			 'Cycle 1' : [120, 10800 , 1],
# 			 'Cycle 2' : [120, 10800 , 1],
# 			 'Cycle 3' : [120, 10800 , 1],
# 			 'Cycle 4' : [120, 10800 , 1],
# 			 'Cycle 5' : [120, 10800 , 1],
# 			 'Cycle 6' : [120, 10800 , 1]}

## specs for useqFISH
# dictionary: 'reagent': [valveA_port, valveB_port]
fluidics_setup = {
	'ssc': [7, 1],
	'hcr': [3, 1],
	'dapi': [2, 1],
	'displacement':[4, 1],
	'stripping': [5, 1],
	'dt': [6, 1],
	'reader1': [1, 1],
	'reader2': [1, 2],
	'reader3': [1, 3],
	'reader4': [1, 4],
	'reader5': [1, 5],
	'reader6': [1, 6],
	'reader7': [1, 7],
	'reader8': [1, 8],
	'flush': [8, 1]
}
# FluidicsSetup = {
# 	'reader1': [1],
# 	'reader2': [2],
# 	'ssc': [5],	# use valveB
# 	'hcr': [4],
# 	'dapi': [3],
# 	'displacement': [6],
# 	'stripping': [7],
# 	'dt': [8]
# }


# ----------------------------------------------------------------------
# Define functions
# ----------------------------------------------------------------------

# Check valve is in correct position, not moving, not overloaded:
#	included bool inputs in case only one valve needs to be checked 
# Do this before starting the pump to ensure the correct reagent goes to sample
#	TO DO: Generalize this function and put in hamilton class instead
def checkValveStatus(port_ID_A, port_ID_B, checkValveA = True, checkValveB = True):
	
	valveA_portCheck = 10 # initialized as 10 b/c port will never be in position 10
	valveB_portCheck = 10
	
	if checkValveA: # Check Valve A
		valveA_status = MVPchain.getStatus(valve_ID=0)
		while not valveA_status[1] or valveA_status[2]:
			print('valve a either still moving or overloaded')
			valveA_status = MVPchain.getStatus(valve_ID = 0)
		valveA_portCheck = valveA_status[0]
	
	if checkValveB: # Check Valve B
		valveB_status = MVPchain.getStatus(valve_ID = 1)
		while not valveB_status[1] or valveB_status[2]:
			print('valve b either still moving or overloaded')
			valveB_status = MVPchain.getStatus(valve_ID = 1)
		valveB_portCheck = valveB_status[0]
	
	# Check if port is in correct position on each valve:
	return (valveA_portCheck == port_ID_A, valveB_portCheck == port_ID_B)

# Check entire fluidics setup
#	(i.e. correct reagent to correct port on correct valve, make sure
#	pump is stopped and remote control is enabled on pump)
def checkFluidics():
	
	response = input('\nWould you like to verify valve setup before running experiment? Y/N: ')
	if response == 'Y' or response =='y':
		MVPchain.checkValveSetup() # goes through each port on each valve	# NEED TO EDIT
			# to confirm each port has the correct reagent (by user-input)
		# To do: confirm correct number of ports per valve first
	
	response = input('\nWould you like to check pump status? Y/N: ')
	if response == 'Y' or response == 'y':
		pumpStatus = pump.getStatus()
		# pumpStatus format = (status, speed, direction, control, auto-start, 'No Error')
		print(pumpStatus)
		if pumpStatus[0] == 'Flowing':
			if pumpStatus[1] != 0.0: # sometimes says "flowing" even if it's stopped at 0 speed
				pump.stopFlow()
			pumpStatus = pump.getStatus()
		if pumpStatus[2] != 'Forward': # make sure pump flows in correct direction
			pump.setFlowDirection(forward = True)
			pumpStatus = pump.getStatus()
		if pumpStatus[3] != 'Remote': # make sure remote control is enabled
			sys.exit('Remote control not confirmed. Exiting...') # stop running program
		# NOTE: this can and should be made more robust in the future
		print('Pump status checked successfully!')

# Check Fusion and input protocol name (user-input)
#	To do: more robust
def checkFusion():
	response = input('\nIs Fusion open and running? Y/N: ')
	if response != 'Y' and response != 'y':
		print('     Please open Fusion software...')
		response = input('\nIs Fusion open and running? Y/N: ')

	response = input('\nIs REST enabled? Y/N: ')
	if response != 'Y' and response != 'y':
		print('     Please enable REST...')
		response = input('\nDo you need assistance enabling REST? Y/N: ')
		if response == 'Y' or response == 'y':
			print('\n1) Select drop-down menu at top right of Fusion called "Imaging"')
			print('2) Select "Preferences"')
			print('3) Select REST API --> Make sure it is toggled "on" and port number is 15120')
			response = input('\nIs REST enabled? Y/N: ')

	# Input protocol name
	protocol = input('\nWhat Fusion protocol would you like to run?\
		\nPlease enter protocol name exactly as it appears in Fusion\n')
	
	# Verify protocol name was typed in correctly (since this will be fed into code later):
	response = input('Confirm ' + protocol + ' is the protocol to be run: Y/N ')
	if response != 'Y' and response != 'y':
		protocol = input('\nWhat Fusion protocol would you like to run?\
			\nPlease enter protocol name exactly as it appears in Fusion\n')
		response = input('Confirm ' + protocol + ' is the protocol to be run: Y/N ')
		# CHECK: Can protocol name be checked in advance or only upon running?
	
	return protocol

# Change and Check Ports
#	TO DO: 
#	1) Turn valve shortest distance to reach port 
#		(e.g. if at port 1, turn CCW for port 8)
#	2) Expand and move to hamilton class, more robust, etc.
def changeAndCheckPort(reagent):
	valveConfig = FluidicsSetup.get(reagent) # get valve config for given reagent
	
	# MVPchain.changePort(pump_ID = 0, valveConfig[0]) # change first valve
	# MVPchain.changePort(pump_ID = 1, valveConfig[1]) # second valve
	
	valveCheck = checkValveStatus(valveConfig[0], valveConfig[1], True, True)
	if not valveCheck[0] or not valveCheck[1]: # if wrong port on either valve (shouldn't happen)
		response = input('Valve in wrong position. Would you like to try again? Y/N: ')
		if response == 'Y' or response == 'y':
			MVPchain.changePort(0, valveConfig[0]) 
			MVPchain.changePort(1, valveConfig[1])
			valveCheck = checkValveStatus(valveConfig[0], valveConfig[1])
		else:
			response = input('Would you like to stop the program? Y/N: ')
			if response == 'Y' or response == 'y':
				sys.exit('Exited the program')		

# Flush entire system tubing with fluid - must be done at start of experiment!!
#	(ensure no air gaps between reagents, make sure no loose fittings, etc.)
# DONE MANUALLY FOR NOW
def systemFlush():
	print('Make sure tubing is connected directly from valve to pump NOT the flow cell!!')
	response = input('Is tubing connected correctly? Y/N ')
	if response != 'Y' and response != 'y':
		print('Please connect tubing directly from MVP valve to pump')
		response = input('Is tubing connected correctly? Y/N ')

	valveA_ports = ['Stripping Buffer', 'PBST', 'Wash/Imaging Buffer', 'Nuclear Stain',\
		'PBS', 'Nissl']
	for i in range(len(valveA_ports)):
		changeAndCheckPort(valveA_ports[i])
		pump.startFlow(speed)
		time.sleep(300) # flow for 5 min
		pump.stopFlow()
	
	# Finish/modify this code based on testing (timing, etc.)

# One step of sequencing (e.g. stripping buffer for cycle 1, PBST for cycle 1, etc.)
def sequencingStep(reagent, test = False):
	changeAndCheckPort(reagent) # change port based on reagent, verify port
	if test == True: # if in testing mode, manually set shorter pumping times
		pumpingSpecs = [240, 5, 2]
		print('Test sequencing')
	else:
		pumpingSpecs = PumpingSpecs.get(reagent)
	for i in range(pumpingSpecs[2]): # number of repeats
		pump.startFlow(speed)
		time.sleep(pumpingSpecs[0]) # leave pump on for specified time
		pump.stopFlow()
		time.sleep(pumpingSpecs[1]) # time incubating in reagent

# Nuclear stain
# TBD

# Nissl stain
def NisslStain():
	# PBST wash - 1 x 10 min.
	changeAndCheckPort('PBST')
	pump.startFlow(speed)
	time.sleep(240) #  leave on for 3 minutes
	pump.stopFlow()
	time.sleep(600) # wash for 10 min.
	
	# PBS wash - 2 x 5 min.
	changeAndCheckPort('PBS')
	for i in range(2): # 2 washes
		pump.startFlow(speed)
		time.sleep(240)
		pump.stopFlow()
		time.sleep(300) # wash for 5 min.

	# Nissl (NeuroTrace) stain - 1 x 20 min.
	sequencingSetp('Nissl')
	
	# PBST - 1 x 10 min.
	changeAndCheckPort('PBST')
	pump.startFlow(speed)
	time.sleep(300) # leave on for 5 min to ensure all stain washed out
	pump.stopFlow()
	time.sleep(600) # wash for 10 min
	
	# PBS - 2 hrs
	changeAndCheckPort('PBS')
	pump.startFlow(speed)
	time.sleep(300) # leave on for 5 min to ensure all PBST washed out
	pump.stopFlow()
	time.sleep(7200) # wash for 2 hrs
		
# Sequencing
#	TO DO: Include code that turns valve the direction of the shortest movement
#		(e.g. if at port #1, turn CCW to get to port #8)

def runSequencing(numCycles, protocolName):
	for i in range(numCycles): # go through sequencing cycles
				
		# Stripping Buffer - 2 x 10 min.
		sequencingStep('Stripping Buffer')
		
		# PBST - 3 x 5 min.
		sequencingStep('PBST')
		
		# Sequencing Mixture - 1 x 3 hr.
		reagent = 'Cycle ' + str(i+1) # i + 1 since port starts at 0
		sequencingStep(reagent)
		
		# Wash/Imaging Buffer - 2 x 10 min.
		sequencingStep('Wash/Imaging Buffer')

		if i == (numCycles-1):
			break
		
		else:
			try:
				fusionrest.run_protocol_completely(protocolName)
			except Exception as ex:
				print('Error running Fusion protocol')

def flow(reagent, time_pumping=0, time_reaction=0, repeats=1, log=None):
	for valve_id in range(MVPchain.num_valves):
		MVPchain.changePort(valve_id, fluidics_setup[reagent][valve_id])

	for repeat in range(repeats):
		current_time = time.localtime()
		current_time_string = time.strftime("%m-%d-%Y %H:%M:%S", current_time)
		print(f">>>>> {reagent} reaction {repeat+1}/{repeats} started at {current_time_string}")
		print(f">>>>> {reagent} reaction {repeat+1}/{repeats} started at {current_time_string}", file=log)
		pump.startFlow(speed)
		time.sleep(time_pumping)
		pump.stopFlow()
		time.sleep(time_reaction)

# def sequencing_step(reagent, time_pumping=time_pumping, time_reaction=0, repeats=1, log=None):
# 	flow(reagent, time_pumping=time_pumping, time_reaction=time_reaction, repeats=repeats, log=log)
	# flow('flush', time_pumping=5, log=log)

    # # changeAndCheckPort(reagent)
	# # 
	# MVPchain.changePort(0, fluidics_setup[reagent][0])
	# MVPchain.changePort(1, fluidics_setup[reagent][1])
	# time.sleep(1)	# sleep 1 sec after changing ports
	# for repeat in range(repeats):
	# 	current_time = time.localtime()
	# 	current_time_string = time.strftime("%H:%M:%S", current_time)
	# 	print(f">>>>> {reagent} reaction {repeat+1}/{repeats} started at {current_time_string}", file=log)
	# 	pump.startFlow(speed)
	# 	time.sleep(time_pumping)
	# 	pump.stopFlow()
	# 	time.sleep(time_reaction)

	# 	MVPchain.changePort(0, fluidics_setup['flush'][0])
	# 	MVPchain.changePort(1, 1)
	# 	pump.startFlow(speed)
	# 	time.sleep(time_pumping)
	# 	pump.stopFlow()


def imaging(round, protocol_name, log=None):
	flow('ssc', time_pumping=time_pumping[0]*2)

	time.sleep(2)
	current_time = time.localtime()
	current_time_string = time.strftime("%m-%d-%Y %H:%M:%S", current_time)
	print(f">>>>> Round #{round+1}, imaging started at {current_time_string}")
	print(f">>>>> Round #{round+1}, imaging started at {current_time_string}", file=log)
	try:
		fusionrest.run_protocol_completely(protocol_name)
		current_time = time.localtime()
		current_time_string = time.strftime("%m-%d-%Y %H:%M:%S", current_time)
		print(f">>>>> Round #{round+1}, imaging finished at {current_time_string}")
		print(f">>>>> Round #{round+1}, imaging finished at {current_time_string}", file=log)
	except Exception:
		current_time = time.localtime()
		current_time_string = time.strftime("%m-%d-%Y %H:%M:%S", current_time)
		print(f"!!!!! Error running Fusion protocol for Round #{round+1} at {current_time_string}")
		print(f"!!!!! Error running Fusion protocol for Round #{round+1} at {current_time_string}", file=log)
	time.sleep(3)

	flow('flush', time_pumping=time_pumping[0]-5)


def run_sequencing(num_rounds, protocol_name, expt_name=" "):
	minute = 60
	# minute = 0
	
	current_date = time.localtime()
	current_date_string = time.strftime("%m-%d-%Y", current_date)
	log_file_name = "log_" + expt_name + "_" + current_date_string + ".txt"
	log_object = open(log_file_name, mode='a+')
    
	flow('ssc', time_pumping=time_pumping[0], time_reaction=1*minute, repeats=1, log=log_object)   # 2xSSC washing

	# imaging(-1, protocol_name, log=log_object)
	for round in range(num_rounds):
		# if round%2 == 0:
		# 	sequencing_step('reader1', time_reaction=30*minute, repeats=1)
		# elif round%2 == 1:
		# 	sequencing_step('reader2', time_reaction=30*minute, repeats=1)

		reagent = 'reader' + str(round%8+1) # i + 1 since port starts at 0
		# reagent = 'reader1'
		flow(reagent, time_pumping=time_pumping[1], repeats=1, log=log_object)
		flow('flush', time_pumping=time_pumping[2], time_reaction=30*minute)

		flow('ssc', time_pumping=time_pumping[0]*2, time_reaction=5*minute, repeats=3, log=log_object)   # 2xSSC washing
		flow('flush', time_pumping=time_pumping[2])
		
		flow('hcr', time_pumping=time_pumping[0], repeats=1, log=log_object)
		flow('flush', time_pumping=time_pumping[2], time_reaction=60*minute)

		flow('ssc', time_pumping=time_pumping[0]*2, time_reaction=5*minute, repeats=3, log=log_object)   # 2xSSC washing
		flow('flush', time_pumping=time_pumping[2])

		flow('dapi', time_pumping=time_pumping[0], repeats=1, log=log_object)
		flow('flush', time_pumping=time_pumping[2], time_reaction=10*minute)

		flow('ssc', time_pumping=time_pumping[0]*2, time_reaction=5*minute, repeats=3, log=log_object) 
		        
		imaging(round, protocol_name, log=log_object)
		
		flow('displacement', time_pumping=time_pumping[0], repeats=1, log=log_object)    
		flow('flush', time_pumping=time_pumping[2], time_reaction=60*minute)

		flow('ssc', time_pumping=time_pumping[0]*2, time_reaction=5*minute, repeats=3, log=log_object)
		flow('flush', time_pumping=time_pumping[2])

		flow('stripping', time_pumping=time_pumping[0], repeats=1, log=log_object)
		flow('flush', time_pumping=time_pumping[2], time_reaction=60*minute)

		flow('ssc', time_pumping=time_pumping[0]*2, time_reaction=5*minute, repeats=5, log=log_object)   # careful washing after stripping

		imaging(round, protocol_name, log=log_object)
	
		
	imaging(round+1, protocol_name, log=log_object)

	flow('dt', time_pumping=time_pumping[0], repeats=1, log=log_object)
	flow('flush', time_pumping=time_pumping[2], time_reaction=60*minute)

	flow('ssc', time_pumping=time_pumping[0]*2, time_reaction=1*minute, repeats=2, log=log_object)
	flow('flush', time_pumping=time_pumping[2])

	flow('dapi', time_pumping=time_pumping[0], repeats=1, log=log_object)
	flow('flush', time_pumping=time_pumping[2], time_reaction=10*minute)

	imaging(round+2, protocol_name, log=log_object)

	log_object.close()
	return True


def flushing(port_for_valve_a, port_for_valve_b):
	pump.startFlow(speed)
	if port_for_valve_a == 1:
		time.sleep(time_pumping[1])
	elif port_for_valve_a > 1:
		time.sleep(time_pumping[0])
	pump.stopFlow()
	print(f">>>> Valve_a::port_{port_for_valve_a}, valve_b::port_{port_for_valve_b} washing done")
	print(f">>>> Take the tubing out")
	os.system("pause")

	pump.startFlow(speed)
	time.sleep(time_pumping[2])
	pump.stopFlow()
	print(f">>>> Valve_a::port_{port_for_valve_a}, valve_b::port_{port_for_valve_b} flushing done")


def run_flushing():
	for port_for_valve_a in range(1, 9):
		MVPchain.changePort(0, port_for_valve_a)
		if port_for_valve_a == 1:
			for port_for_valve_b in range(1, 9):
				MVPchain.changePort(1, port_for_valve_b)
				flushing(port_for_valve_a, port_for_valve_b)
		else:
			MVPchain.changePort(1, 1)
			flushing(port_for_valve_a, 1)

	return True

def run_test():
	while True:
		flow('reader1', time_pumping=time_pumping[1], repeats=1)
		flow('flush', time_pumping=time_pumping[2], time_reaction=5)

		flow('dapi', time_pumping=time_pumping[0], repeats=1)
		flow('flush', time_pumping=time_pumping[2], time_reaction=5)

		os.system("pause")
	
	return True
	

# --------------------------------------------------------------------------
if __name__ == '__main__':

	# ----------------------------------------------------------------------
	# Initialize pump and fluidics valves
	# ----------------------------------------------------------------------

	print('Initializing Fluidics Setup')
	print('...........................')
	MVPchain = HamiltonMVP(com_port='COM7', verbose=True)
	# print(MVPchain.__dict__)
	# MVPchain.changePort(0, 2)
	pump = APump(com_port='COM8', verbose=True)
	
	# # testing be fore experiment
	# status = run_test()
	
	# # experiment
	# status = run_sequencing(3, 'Min_5channel', expt_name='3_probe_useqFISHv2_POC')
	# if status:
	# 	print(f">>>>> Experiment went smoothly")	 

	# for washing after experiment
	status = run_flushing()
	if status:
		print(f">>>>> System cleaning went smoothly")


	# minute = 60
	# round = 1
	# protocol_name = 'Min_5channel'
	# sequencing_step('displacement', time_reaction=60*minute, repeats=1)    
	# sequencing_step('ssc', time_reaction=1*minute, repeats=2)
	# sequencing_step('stripping', time_reaction=60*minute, repeats=1)
	# sequencing_step('ssc', time_reaction=1*minute, repeats=3)   # careful washing after stripping

	# print(f">>>>> Round #{round+1}, after stripping, imaging started")
	# try:
	# 	fusionrest.run_protocol_completely(protocol_name)
	# 	print(f">>>>> Round #{round+1}, after stripping, imaging finished")
	# except Exception:
	# 	print(f"!!!!! Error running fusion protocol for Round #{round+1}, after stripping")
	# os.system("pause")

	pump.closeRemote() # stop remote control; enable keypad control
	MVPchain.closeSerialPort() # disconnect MVP valve chain from serial
