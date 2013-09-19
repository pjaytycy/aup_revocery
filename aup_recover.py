import glob
import os
import struct

MAGIC_VAL_AU = 0x2e736e64

def get_last_write_time(filepath):
  return os.stat(filepath).st_mtime

def get_aup_start(projname):
  return """<?xml version="1.0" standalone="no" ?>
<!DOCTYPE project PUBLIC "-//audacityproject-1.3.0//DTD//EN" "http://audacity.sourceforge.net/xml/audacityproject-1.3.0.dtd" >
<project xmlns="http://audacity.sourceforge.net/xml/" projname="%s_data" version="1.3.0" audacityversion="2.0.3" sel0="0.0000000000" sel1="0.0000000000" vpos="0" h="5153.6805442177" zoom="86.1328125000" rate="44100.0">
	<tags/>
""" % (projname, )

def get_wavetrack_start(channel, linked):
  return """	<wavetrack name="Audio Track" channel="%d" linked="%d" mute="0" solo="0" height="150" minimized="0" isSelected="0" rate="44100" gain="1.0" pan="0.0">
		<waveclip offset="0.00000000">
""" % (channel, linked)

def get_sequence_start(maxsamples, sumsamples):
  return """			<sequence maxsamples="%d" sampleformat="262159" numsamples="%d">
""" % (maxsamples, sumsamples)
  
def get_waveblock(start, filename, len):
  return """				<waveblock start="%d">
					<simpleblockfile filename="%s" len="%d" min="-1.0" max="1.0" rms="0.1"/>
				</waveblock>
""" % (start, filename, len)

def get_sequence_wavetrack_stop():
  return """			</sequence>
			<envelope numpoints="0"/>
		</waveclip>
	</wavetrack>
"""

def add_wavetrack(f_aup, filepath_list, channel, linked, other_channel_filepath_list):
  f_aup.write(get_wavetrack_start(channel, linked))
  
  waveblocks = ""
  maxsamples = 0
  sumsamples = 0
  for filepath, other_filepath in zip(filepath_list, other_channel_filepath_list):
    print "adding", os.path.basename(filepath)
    f = open(filepath, "rb")
    data = f.read(8)
    magic_val, offset = struct.unpack("<Ii", data)
    if magic_val != MAGIC_VAL_AU:
      f = open(other_filepath, "rb")
      data = f.read(8)
      magic_val, offset = struct.unpack("<Ii", data)
      if magic_val != MAGIC_VAL_AU:
        print "error: magic value does not match"
        print os.path.basename(filepath), os.path.basename(other_filepath)
        print "0x%08x != 0x%08x" % (magic_val, MAGIC_VAL_AU)
        waveblocks += "-- corrupt files: %s, %s\n" % (os.path.basename(filepath), os.path.basename(other_filepath))
        continue
      else:
        filepath = other_filepath
    
    size = os.stat(filepath).st_size
    if ((size - offset) % 4) != 0:
      print "error: non-integer number of samples"
      print filepath
      print "size = %d, offset = %d" % (size, offset)
      waveblocks += "-- corrupt file: %s\n" % filepath
      continue
      
    numsamples = (size - offset) / 4
    
    waveblocks += get_waveblock(sumsamples, os.path.basename(filepath), numsamples)

    sumsamples += numsamples
    maxsamples = max(maxsamples, numsamples)

  f_aup.write(get_sequence_start(maxsamples, sumsamples))
  f_aup.write(waveblocks)
  f_aup.write(get_sequence_wavetrack_stop())
  
def create_aup(dir, projname):
  data_dir = os.path.join(dir, projname + "_data")
  filepath_list = glob.glob(os.path.join(data_dir, "e*", "d*", "*.au"))
  sorted_filepath_list = sorted(filepath_list, key = get_last_write_time)
  even_filepath_list = sorted_filepath_list[0::2]
  odd_filepath_list = sorted_filepath_list[1::2]

  f_aup = open(os.path.join(dir, projname + ".aup"), "wb")
  f_aup.write(get_aup_start(projname))
  
  add_wavetrack(f_aup, even_filepath_list, channel = 0, linked = 1, other_channel_filepath_list = odd_filepath_list)
  add_wavetrack(f_aup, odd_filepath_list, channel = 1, linked = 0, other_channel_filepath_list = even_filepath_list)
  
  f_aup.write("</project>\n")
  f_aup.close()

