#!/usr/bin/env python

import os
import sys
import subprocess
import string
import zipfile
import requests
import json
import struct
import re
import shutil

import trim

def Blank_Width():
  return 20

def Zero_reset():
  return 5

def Data_reset():
  return 10

def Data_match():
  return 100

def Sensitivity():
  return 0.05


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
    self.key = -1
    elem = self.filename.split(oodict["splitter"])
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
      val = (int(elem[1]) + 2) * 12 + self.nttonb_dict[elem[0]] 
    if re.match("[A-G][b-s][0-9]", note):
      val = (int(elem[2]) + 2) * 12 + self.nttonb_dict[elem[0]+elem[1]]
    return val



def nb_to_note(nb):
  oct = nb/12 - 1


# Sample map parser
def fill_key_perc(sample_map):
  for smpl in sample_map.items():
    #for smpl in sample_list[1]:
      smpl[1][0].lokey = smpl[1][0].hikey = smpl[1][0].key

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
      smpl.hikey = key_current + diff // 2
    for smpl in sample_map[key_next]:  
      smpl.lokey = key_current + diff // 2 + 1

def fill_vel(sample_map):
  for sample_list in sample_map.items():
    if len(sample_list[1]) != 1:
      val = 0
      vel_range = 127 // len(sample_list[1])
      for smpl in sample_list[1]:
        smpl.lovel = val
        val += vel_range
        if val > 120 : val = 127
        smpl.hivel = val - 1

def fill_samplemap(sample_list):
  sample_map = dict()
  for i, smpl in enumerate(sample_list):
    smpl_class = sample(smpl)
    if smpl_class.key == -1: 
      smpl_class.key = 48 + i
    if smpl_class.key in sample_map:
      sample_map[smpl_class.key].append(smpl_class) 
    else:
      tmp = list()
      tmp.append(smpl_class)
      sample_map[smpl_class.key] = tmp
  return sample_map



#sort phil sample
def lgth_filter(filename):
  elem = filename.split("_")
  if re.match("[0-9]+", elem[2]):
    return True
  else:
    return False

def sort_lgth(filename):
  path=""
  elem = os.path.basename(filename).split("_")

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


print("Using orchestra ", str(sys.argv[1]))


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
      dst_file = dwnld_dir + os.path.basename(instru["url"]).replace("%20", "_")

      if not os.path.exists(dst_file) :
        #Download
        print("Downloading ", oodict["input url"], instru["url"] )
        response = requests.get(oodict["input url"] + instru["url"], stream=True)
        with open(dst_file, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

      #Create output dir for unzipped sample
      xtract_dir = tmp_dir + "/xtract/" + grp + "/" + instru["name"] + "/"
      if not os.path.exists(xtract_dir):
        os.makedirs(xtract_dir)

      #Extract
      if not os.listdir(xtract_dir):
        print("Extract ", dst_file)
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

      #list dir recursively
      audiofile = list()
      for inifile in os.listdir(xtract_dir):
        if (inifile==".") or (inifile==".."):
          continue
        if os.path.isdir(xtract_dir + inifile):
          for iniifile in os.listdir(xtract_dir + inifile):
            if (inifile==".") or (inifile==".."):
              continue
            audiofile.append(inifile + "/" + iniifile)
        else:
          audiofile.append(inifile)
             

      #Transcode
      for infile in audiofile:
        print("transcoding : ", infile)
        #if oodict["key"] == "phil":
        if instru["sort"] == "lgth":
          if not lgth_filter(infile):
            print("Jump file as it's not a note")
            continue
        if (infile==".") or (infile==".."):
          continue
        outfile = wav_sample_dir + os.path.splitext(os.path.basename(infile))[0] + ".wav"
        try:
          cmd = ["sox", xtract_dir + infile, outfile]
          #print("command :", str(cmd))
          subprocess.call(cmd)
        except OSError as e:
          print("SOX programm for converting audio files has encounter a problem : ") 
          print("ERRNO ", str(e.errno), " : ", e.strerror)
          exit()


###############
#Blank remover
###############

        #Create output dir for unblanked sample
        sfz_sample_dir = out_dir + "/" + grp + "/" + instru["name"] + "/"
        if not os.path.exists(sfz_sample_dir):
          os.makedirs(sfz_sample_dir)


        #Prepare for copying
        #idx = trim.getSimpleTrim(outfile)
        idx = trim.getNRJTrim(outfile)
        try:
          with open(outfile, 'rb') as audio_file:

            wh = audio_file.read(Wave_Header_Size())
            whd = struct.unpack(wave_header_fmt, wh)
            #print whd[0] 
            fh = audio_file.read(Fmt_Header_Size())
            fhd = struct.unpack(fmt_header_fmt, fh)

            audio_file.read(fhd[1] - Fmt_Header_Size() + 8)
            #if data is not PCM => extended header
            if fhd[2] != 1:
              facth = audio_file.read(8)
              facthd = struct.unpack("II", facth)
              factdatah = audio_file.read(facthd[1])
              print(facthd[1])



            lgth = ""
            #if oodict["key"] == "phil":
            if instru["sort"] == "lgth":
              lgth = sort_lgth(outfile)
              if not os.path.exists(sfz_sample_dir + lgth):
                os.makedirs(sfz_sample_dir + lgth)

            blank_out_file =  sfz_sample_dir + lgth + os.path.splitext(os.path.basename(outfile))[0] + ".wav"
            audio_file.seek(0)
            with open(blank_out_file, 'wb') as bo_file: 
            #WAVE HEADER 
              #copy RIFF
              bo_file.write(audio_file.read(4))
              #change & write size - idx
              bo_file.write(struct.pack("I", struct.unpack("I", audio_file.read(4))[0] - idx))
              #copy WAVE
              bo_file.write(audio_file.read(4))
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


        except IOError :
          print("Error opening file, next ", outfile)
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
        print("Create SFZ file : ", sfz_file_name)
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
          if instru["sort"] == "perc":
             fill_key_perc(sample_map)
          else:
             fill_key(sample_map)  
          #fill vel
          fill_vel(sample_map)

          for sample_list in sample_map.items():
            for smpl in sample_list[1]:
              sfz_file.write("<region>\n")
              #if oodict["key"] == "phil":
              if instru["sort"] == "lgth":
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

