#!/usr/bin/env python

#Copyright (c) 2013, Eduard Broecker 
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that
# the following conditions are met:
#
#    Redistributions of source code must retain the above copyright notice, this list of conditions and the
#    following disclaimer.
#    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#    following disclaimer in the documentation and/or other materials provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#DAMAGE.

#
# this script imports excel-files to a canmatrix-object
# these Excelfiles should have following collums:
# ID, Frame Name, Cycle Time [ms], Launch Type, Launch Parameter, Signal Byte No., Signal Bit No., Signal Name, Signal Function,  Signal Length [Bit], Signal Default, Signal Not Available, [LIST OF ECUS], Value,	Name / Phys. Range,	Function / Increment Unit	 
#

from library.canmatrix import *
import xlrd
import codecs

def importXls(filename):
	wb = xlrd.open_workbook(filename, formatting_info=True)
	sh = wb.sheet_by_index(0)
	db = CanMatrix()
	
	# eval search for correct collums:
	index = {}
	for i in range(sh.ncols):
		value = sh.cell(0,i).value
		if  value == "ID":
			index['ID'] = i
		elif "Frame Name" in value:
			index['frameName'] = i
		elif "Cycle" in value:
			index['cycle'] = i
		elif "Launch Type" in value:
			index['launchType'] = i
		elif "Launch Parameter" in value:
			index['launchParam'] = i
		elif "Signal Byte No." in value:
			index['startbyte'] = i
		elif "Signal Bit No." in value:
			index['startbit'] = i
		elif "Signal Name" in value:
			index['signalName'] = i
		elif "Signal Function" in value:
			index['signalComment'] = i
		elif "Signal Length" in value:
			index['signalLength'] = i
		elif "Signal Default" in value:
			index['signalDefault'] = i
		elif "Signal Not Ava" in value:
			index['signalSNA'] = i
		elif "Value" in value:
			index['Value'] = i
		elif "Name / Phys" in value:
			index['ValueName'] = i
		elif "Function /" in value:
			index['function'] = i
			
	index['BUstart'] = index['signalSNA'] + 1
	index['BUend'] = index['Value'] - 1

	#BoardUnits:
	for x in range(index['BUstart'],index['BUend']):
		db._BUs.add(BoardUnit(sh.cell(0,x).value))	

	#initialize with first Frame:
	frameId = sh.cell(2,index['ID'])
	signalName = ""
	newBo = None
	for rownum in range(2,sh.nrows):
		if sh.cell(rownum,index['ID']).value != frameId:
			sender = []
			# new Frame
			frameId = sh.cell(rownum,index['ID']).value
			frameName = sh.cell(rownum,index['frameName']).value
			cycleTime = sh.cell(rownum,index['cycle']).value
			launchType = sh.cell(rownum,index['launchType']).value
			dlc = 8
			launchParam = sh.cell(rownum,index['launchParam']).value
			if type(launchParam).__name__ != "float":
				launchParam = 0.0
			launchParam = str(int(launchParam))
			# TODO: correct DLC ermitteln
			newBo = Botschaft(int(frameId[:-1], 16), frameName, dlc, None)
			db._bl.addBotschaft(newBo)
			if launchType is not None:
				if "Cyclic+Change" == launchType:
					newBo.addAttribute("GenMsgSendType", "5")	
					newBo.addAttribute("GenMsgDelayTime", launchParam)
				elif "Cyclic" == launchType:
					newBo.addAttribute("GenMsgSendType", "0")
				elif "BAF" == launchType:
					newBo.addAttribute("GenMsgSendType", "2")
					newBo.addAttribute("GenMsgNrOfRepetitions", launchParam)
				elif "DualCycle" == launchType:
					newBo.addAttribute("GenMsgSendType", "8")
					newBo.addAttribute("GenMsgCycleTimeActive", launchParam)
				elif "None" == launchType:
					newBo.addAttribute("GenMsgSendType", "10")
					newBo.addAttribute("GenMsgDelayTime", launchParam)
				elif "OnChange" == launchType:
					newBo.addAttribute("GenMsgSendType", "9")
					newBo.addAttribute("GenMsgNrOfRepetitions", launchParam)
				elif "Spontaneous" == launchType:
					newBo.addAttribute("GenMsgSendType", "1")
					newBo.addAttribute("GenMsgDelayTime", launchParam)

			if type(cycleTime).__name__ != "float":
				cycleTime = 0.0
			newBo.addAttribute("GenMsgCycleTime", str(int(cycleTime)))
	
		if sh.cell(rownum,index['signalName']).value != signalName:
			# new Signal
			reciever = []
			startbyte = int(sh.cell(rownum,index['startbyte']).value)
			startbit = int(sh.cell(rownum,index['startbit']).value)
			signalName = sh.cell(rownum,index['signalName']).value	
			signalComment = sh.cell(rownum,index['signalComment']).value	
			signalLength = int(sh.cell(rownum,index['signalLength']).value)
			signalDefault = sh.cell(rownum,index['signalDefault']).value
			signalSNA = sh.cell(rownum,index['signalSNA']).value

			byteorder = 1 # Default Intel
			#TODO, this is NOT in .xls?!
			valuetype = '+'
			if signalLength > 8:
				byteorder = 0 # Motorola for long signals
				
			if signalName != "-":
				for x in range(index['BUstart'],index['BUend']):
					if 's' in sh.cell(rownum,x).value:
						newBo.addTransmitter(sh.cell(0,x).value.strip())
					if 'r' in sh.cell(rownum,x).value:
						reciever.append(sh.cell(0,x).value.strip())
				if signalLength > 8:
					newSig = Signal(signalName, startbyte*8+startbit-signalLength, signalLength, byteorder, valuetype, 1, 0, 0, 1, "", reciever, None)
				else:
					newSig = Signal(signalName, startbyte*8+startbit, signalLength, byteorder, valuetype, 1, 0, 0, 1, "", reciever, None)
				
				newBo.addSignal(newSig)
				newSig.addComment(signalComment)
				function = sh.cell(rownum,index['function']).value
		value = sh.cell(rownum,index['Value']).value
		valueName = sh.cell(rownum,index['ValueName']).value
		if valueName == 0:
			valueName = "0"
		elif valueName == 1:
			valueName = "1"
		test = valueName
		#.encode('utf-8')

		factor = 0
		unit = ""
		if ".." in test:
			(mini, maxi) = test.strip().split("..",2)
			unit = ""
			if " " in maxi:
				(maxi, unit) = maxi.strip().split(" ",2)
			factor = sh.cell(rownum,index['function']).value
			if type(factor).__name__ == "unicode":
				factor = factor.strip()
				if " " in factor:
					(factor, temp) = factor.split(" ",2)
			newSig._factor = float(factor)
			newSig._offset = float(mini)
			newSig._unit = unit
		elif valueName.__len__() > 0:
			value = int(value)
			newSig.addValues(value, valueName)
	
	#do dlc-correction:
	for bo in db._bl._liste:
		maxBit = 0
		for sig in bo._signals:
			if int(sig._startbit) + int(sig._signalsize) > maxBit:
				maxBit = int(sig._startbit) + int(sig._signalsize)
			if bo._Size < (maxBit / 8):
				bo._Size = min(8,int(maxBit / 8))
	return db

importXls("body.xls")