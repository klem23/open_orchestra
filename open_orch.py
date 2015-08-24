#!/usr/bin/env python

import os
import sys
import subprocess
import string
import zipfile
import urllib
import json
import struct
import re
import shutil


def Blank_Width():
  return 20

def Zero_reset():
  return 5

def Data_reset():
  return 10

def Data_match():
  return 100

def Sensitivity():
  return 0.01


#########################
# Sample Parser & Manager
#########################

#class for managing sample mapping
class sample:

  nttonb_dict = { "C":0,"Cs":1,"Db":1,"D":2,"Ds":3,"Eb":3,"E":4,"F":5,"Fs":6,"Gb":6,"G":7,"Gs":8,"Ab":8,"A":9,"As":10,"Bb":10,"B":11}
  nbtont_dict = { nb:nt for nt,nb in nttonb_dict.items()}

  def __init__(self, file):
    self.filename = file
    self.vel = -1
    elem = string.split(self.filename, oodict["splitter"])
    for tag in elem:
      if re.match("[A-G][0-9]", tag) or re.match("[A-G][b-s][0-9]", tag):
        self.key = self.note_to_nb(tag) 
      elif "mezzo" in tag: 
        self.vel = 2
      elif "pianissimo" in tag:
        self.vel = 0
      elif "piano" in tag:
        self.vel = 1
      elif "forte" in tag:
        self.vel = 3
      elif "fortissimo" in tag:
        self.vel = 4

  #function to translate note to midi number
  
  def note_to_nb(self, note):
    elem = list(note)
    if re.match("[A-G][0-9]", note):
      val = (int(elem[1]) + 1) * 12 + self.nttonb_dict[elem[0]] 
    if re.match("[A-G][b-s][0-9]", note):
      val = (int(elem[2]) + 1) * 12 + self.nttonb_dict[elem[0]+elem[1]]
    return val



def nb_to_note(nb):
  oct = nb/12 - 1


# Sample map parser

def fill_key(sample_map):
  #first samples
  for smpl in sample_map[sorted(sample_map.keys())[0]]:
    smpl.lokey = smpl.key - 3
  #last samples
  #for smpl in sample_map[sorted(sample_map.keys())[len(sample_map) - 1]]:
  for smpl in sample_map[sorted(sample_map.keys())[-1]]:
    smpl.hikey = smpl.key + 3

  for idx in range(len(sample_map) - 1):
    key_current = sorted(sample_map.keys())[idx]
    key_next = sorted(sample_map.keys())[idx + 1]
    diff = key_next - key_current
    for smpl in sample_map[key_current]:  
      smpl.hikey = key_current + diff / 2
    for smpl in sample_map[key_next]:  
      smpl.lokey = key_current + diff / 2 + 1

def fill_vel(sample_map):
  for sample_list in sample_map.items():
    if len(sample_list[1]) != 1:
      val = 0
      vel_range = 127 / len(sample_list[1])
      for smpl in sample_list[1]:
        smpl.lovel = val
        val += vel_range
        if val > 120 : val = 127
        smpl.hivel = val

def fill_samplemap(sample_list):
  sample_map = dict()
  for smpl in sample_list:
    smpl_class = sample(smpl)
    if sample_map.has_key(smpl_class.key):
      sample_map[smpl_class.key].append(smpl_class) 
    else:
      tmp = list()
      tmp.append(smpl_class)
      sample_map[smpl_class.key] = tmp
  return sample_map



#sort phil sample
def phil_filter(filename):
  elem = string.split(filename, "_")
  if re.match("[0-9]+", elem[2]):
    return True
  else:
    return False

def phil_sort_lgth(filename):
  path=""
  nosuffix = string.split(filename,".")
  elem = string.split(nosuffix[0], "_")

  if elem[2] == "025":
    path = "/very-short"
  elif elem[2] == "05":
    path =  "/short"
  elif elem[2] == "1":
    path =  "/long"
  elif elem[2] == "15":
    path =  "/very-long"

  if "normal" in elem[-1]:
    path += "/"
  else:
    path += "_" + elem[-1] + "/" 
  
  return path


#wav file header format
wave_header_fmt = "III"
fmt_header_fmt = "IIHHIIHH"
data_header_fmt = "II"

def Wave_Header_Size():
  return 12

def Fmt_Header_Size():
  return 24

def Data_Header_Size():
  return 8

instru_group = ["brass", "wood", "string", "perc"]

##########
#Main Code
##########


print "Using orchestra " + str(sys.argv[1])


############
#Get samples
############

#open json dict for corresponding orchestra
with open(str(sys.argv[1])) as data_file:    
  oodict = json.load(data_file)

  tmp_dir = oodict['temp directory']
  dwnld_dir = oodict['download directory']
  out_dir = oodict['output directory']

#check temp and dwlnd directory
if not os.path.exists(tmp_dir):
  os.makedirs(tmp_dir)
if not os.path.exists(dwnld_dir):
  os.makedirs(dwnld_dir)
if not os.path.exists(out_dir):
  os.makedirs(out_dir)

shutil.copyfile("./" + oodict['license'], out_dir + "/License") 

for grp in instru_group : 
  if grp in oodict:
    for instru in oodict[grp] :

      #zip destination file
      dst_file = dwnld_dir + string.replace(os.path.basename(instru["url"]), "%20", "_")

      if not os.path.exists(dst_file) :
        #Download
	print "Downloading " + oodict["input url"] + instru["url"]
        urllib.urlretrieve (oodict["input url"] + instru["url"], dst_file)

      #Create output dir for unzipped sample
      xtract_dir = tmp_dir + "/xtract/" + grp + "/" + instru["name"] + "/"
      if not os.path.exists(xtract_dir):
        os.makedirs(xtract_dir)

      #Extract
      if not os.listdir(xtract_dir):
        print "Extract " + dst_file
        file_zip = zipfile.ZipFile(dst_file, "r")
        file_zip.extractall(xtract_dir)
        file_zip.close()


###########
#Transcode
###########

      #Create output dir for transcoded sample
      wav_sample_dir = tmp_dir + "/transcode/" + grp + "/" + instru["name"] + "/"
      if not os.path.exists(wav_sample_dir):
        os.makedirs(wav_sample_dir)

      #Transcode
      for infile in os.listdir(xtract_dir):
        print "transcoding : " + infile
        if oodict["key"] == "phil":
          if not phil_filter(infile):
            print "Jump file as it's not a note"
            continue
	if (infile==".") or (infile=="..") :
	  continue
        outfile = wav_sample_dir + os.path.splitext(infile)[0] + ".wav"
        try:
	  cmd = ["sox", xtract_dir + infile, outfile]
	  #print "command :" + str(cmd)
          subprocess.call(cmd)
        except OSError as e:
	  print "SOX programm for converting audio files has encounter a problem : " 
	  print "ERRNO " + str(e.errno) + " : " + e.strerror
	  exit()


###############
#Blank remover
###############

        #Create output dir for unblanked sample
        sfz_sample_dir = out_dir + "/" + grp + "/" + instru["name"] + "/"
        if not os.path.exists(sfz_sample_dir):
          os.makedirs(sfz_sample_dir)



        print "Blank remover " + outfile
        try:
          with open(outfile, 'rb') as audio_file: 

	    wh = audio_file.read(Wave_Header_Size())
            whd = struct.unpack(wave_header_fmt, wh)

            #print whd[0] 

            fh = audio_file.read(Fmt_Header_Size())
            fhd = struct.unpack(fmt_header_fmt, fh)

            print fhd[1]

            #audio format
            print "format " + str(fhd[2])
            #channels
            print "channels " + str(fhd[3])
            #srate
            print "srate " + str(fhd[4])
            #bitdepth
            print "bitdepth " + str(fhd[7])

            if fhd[7] == 8:
              smpl_fmt = "B"
              smpl_size = 1
#              smpl_treshold = Sensitivity() * 
            elif fhd[7] == 16:
              smpl_fmt = "h"
              smpl_size = 2 
              smpl_treshold = Sensitivity() * 0x7FFF 
	      print "treshold " + str(smpl_treshold)
            elif fhd[7] == 24:
              smpl_fmt = "bbb"
              smpl_size = 3
              smpl_treshold = Sensitivity() * 0x7FFFFF 
	      print "treshold " + str(smpl_treshold)
            elif fhd[7] == 32:
              smpl_fmt = "i"
              smpl_size = 4
              smpl_treshold = Sensitivity() * 0x7FFFFFFF 
	      print "treshold " + str(smpl_treshold)

            audio_file.read(fhd[1] - Fmt_Header_Size() + 8)

            #if data is not PCM => extended header
            if fhd[2] != 1:
              facth = audio_file.read(8)
              facthd = struct.unpack("II", facth)
              factdatah = audio_file.read(facthd[1])	
              print facthd[1]
          

            dh = audio_file.read(Data_Header_Size())
            dhd = struct.unpack(data_header_fmt, dh)
            print "data size " + str(dhd[1])


            #get max amp and calcul blank remover treshold
            data_pos = audio_file.tell();

            amp_min = 0;
            amp_max = 0;
	    data_amp = audio_file.read(smpl_size)
            while data_amp:
	      val_tmp = struct.unpack(smpl_fmt, data_amp)
              if smpl_size == 3:
		val = val_tmp[0] + (val_tmp[1] << 8) + (val_tmp[2] << 16)
	      else:
		val = val_tmp[0]
              if val > amp_max: amp_max = val
              elif val < amp_min: amp_min = val
	      data_amp = audio_file.read(smpl_size)

            if amp_max >= - amp_min:
              smpl_treshold = Sensitivity() * amp_max
            else:
              smpl_treshold = Sensitivity() * -amp_min

	    audio_file.seek(data_pos)

          #audio_file.lseek(WAVE_HEADER)
	    data = audio_file.read(smpl_size)
            idx = 0;
            zero_counter = 0
            data_counter = 0
            while data:
	      val_tmp = struct.unpack(smpl_fmt, data)
              if smpl_size == 3:
		val = val_tmp[0] + val_tmp[1] * 0xFF + val_tmp[2] * 0xFFFF
		#val = val_tmp[0] + val_tmp[1] << 8 + val_tmp[2] << 16
		#val = val_tmp[1]
	      else:
		val = val_tmp[0]
	      #if val != 0:
		#found = False
		#for i in range(0, Blank_Width() - 1):
	        #  val = struct.unpack(smpl_fmt, audio_file.read(smpl_size))[0]
                #  if val == 0:
                #   found = True
                #   break
                #if not found:
                #  print "stop :" + str(idx)
                #  break
                #else:
                #  idx += smpl_size * Blank_Width()
	      #data = audio_file.read(smpl_size)
	      #idx += smpl_size;

              if ( val <= 0 and val > - smpl_treshold ) or (val >= 0 and val < smpl_treshold ):
                zero_counter += 1
              else:
                data_counter += 1

              if zero_counter == Zero_reset():
                data_counter = 0
              elif data_counter == Data_reset():
                zero_counter = 0
              elif data_counter >= Data_match():
                break
          
	      #data = audio_file.read(Blank_Width())
	      data = audio_file.read(smpl_size)
              idx += smpl_size
            idx -= Data_match()
            idx -= idx % (fhd[3] * smpl_size)
            print "final idx :" + str(idx)


          #Prepare for copying
            lgth = ""
            if oodict["key"] == "phil":
              lgth = phil_sort_lgth(infile)
              if not os.path.exists(sfz_sample_dir + lgth):
                os.makedirs(sfz_sample_dir + lgth)

            blank_out_file =  sfz_sample_dir + lgth + os.path.splitext(infile)[0] + ".wav"
            audio_file.seek(0)
            with open(blank_out_file, 'wb') as bo_file: 
              #WAVE HEADER 
              bo_file.write(audio_file.read(4))
              bo_file.write(struct.pack("I", struct.unpack("I", audio_file.read(4))[0] - idx))
              bo_file.write(audio_file.read(4))
          #copy RIFF
          #change & write size - idx
          #copy WAVE
              #FMT header
              #bo_file.write(audio_file.read(24))
              bo_file.write(audio_file.read(8 + fhd[1]))
              #if data is not PCM => extended header
              if fhd[2] != 1:
                bo_file.write(audio_file.read(8 + facthd[1]))
          
              #DATA 
              bo_file.write(audio_file.read(4))
              bo_file.write(struct.pack("I", struct.unpack("I", audio_file.read(4))[0] - idx))
              audio_file.seek(idx, 1)
              bo_file.write(audio_file.read())


	  #wave_header -> new size
	  #copy file without zero
        except IOError :
          print "Error opening file, next " + outfile
          continue

##################
#SFZ file writing
##################

      lgth_list = os.listdir(out_dir + "/" + grp + "/" + instru["name"] + "/")
      if os.path.isfile(out_dir + "/" + grp + "/" + instru["name"] + "/" + lgth_list[0]):
        lgth_list = "_"

      for lgth_path in lgth_list:
        if lgth_path == "_":
          lgth_path = ""
          sfz_file_name = out_dir + "/" + grp + "/" + instru["name"] + ".sfz"
        else:
          sfz_file_name = out_dir + "/" + grp + "/" + instru["name"] + "_" + lgth_path + ".sfz"
        print "Create SFZ file : " + sfz_file_name
        with open(sfz_file_name, 'w') as sfz_file: 
          sfz_file.write("// ----------------------\n")
          sfz_file.write("//  Open Orchestra\n")
          sfz_file.write("// ----------------------\n")
          sfz_file.write("//  " + oodict["orchestra name"] + "\n")
          sfz_file.write("// ---------------------- \n")
          sfz_file.write("//  " + instru["name"] + " " + lgth_path + "\n")
          sfz_file.write("// ---------------------- \n\n\n\n")


          sfz_file.write("<group>\n")
          sfz_file.write("\n")

	

          #list audiofile
          sample_list = os.listdir(out_dir + "/" + grp + "/" + instru["name"] + "/" + lgth_path + "/")
          #create map
          sample_map = fill_samplemap(sample_list)
          #sort main list (key) 
          #sample_map.sort(key = lambda sample_list : sample_list[0])
          #sort sub list (vel)
          for sample_list in sample_map.items():
            sample_list[1].sort(key = lambda sample : sample.vel)
          #fill key
          fill_key(sample_map)  
          #fill vel
          fill_vel(sample_map)

          for sample_list in sample_map.items():
            for smpl in sample_list[1]:
              sfz_file.write("<region>\n")
              if oodict["key"] == "phil":
                sfz_file.write("sample=" + instru["name"] + "/" + lgth_path + "/" + smpl.filename + "\n")
              else:
                sfz_file.write("sample=" + instru["name"] + "/" + smpl.filename + "\n")
              sfz_file.write("pitch_keycenter=" + str(smpl.key) +"\n")
              sfz_file.write("lokey=" + str(smpl.lokey) + "\n")
              sfz_file.write("hikey=" + str(smpl.hikey) + "\n")
              if hasattr(smpl, "lovel") and hasattr(smpl, "hivel"): 
                sfz_file.write("lovel=" + str(smpl.lovel) + "\n")
                sfz_file.write("hivel=" + str(smpl.hivel) + "\n")
                
              sfz_file.write("\n")

