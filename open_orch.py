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
import sfz




###########################
#sort phil sample by length
###########################
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

  if "pizz" in elem[-1]:
    path += "_pizz"

  if "normal" in elem[-1]:
    path += "/"
  else:
    path += "_" + os.path.splitext(elem[-1])[0] + "/" 
  
  return path




##########
#Main Code
##########
instru_group = ["brass", "wood", "string", "perc"]

if len(sys.argv) < 2:
  print("Give a json sample dictionary please")
  exit()

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

#get trim algorithm choice
if(len(sys.argv) > 2):
  trimA = sys.argv[2]
else:
   trimA = "NRJ"

if(len(sys.argv) > 3):
  sensitivity = sys.argv[3]
else:
  sensitivity = 0.05



for grp in instru_group : 
  if grp in oodict:
    for instru in oodict[grp] :

############################
#Downlad and extract archive
############################

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
      for i, infile in enumerate(audiofile):
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

        #Create output dir for trimmed sample
        sfz_sample_dir = out_dir + "/" + grp + "/" + instru["name"] + "/"
        if not os.path.exists(sfz_sample_dir):
          os.makedirs(sfz_sample_dir)


        lgth = ""
        if instru["sort"] == "lgth":
          lgth = sort_lgth(outfile)
          if not os.path.exists(sfz_sample_dir + lgth):
            os.makedirs(sfz_sample_dir + lgth)

        #more perc than midi note
        if instru["sort"] == "perc_cut":
          if i <= 60: lgth = "/1/"
          if i > 60 and i <= 120: lgth = "/2/"
          if i > 120: lgth = "/3/"
          if not os.path.exists(sfz_sample_dir + lgth):
            os.makedirs(sfz_sample_dir + lgth)


        #trim with SOX
        blank_out_file =  sfz_sample_dir + lgth + os.path.splitext(os.path.basename(outfile))[0] + ".wav"
        if trimA == "SOX":
          try:
            cmd = ["sox", outfile, blank_out_file, " silence ",  sensitivity, " 1%"]
            #print("command :", str(cmd))
            subprocess.call(cmd)
          except OSError as e:
            print("SOX programm for trimming audio files has encounter a problem : ")
            print("ERRNO ", str(e.errno), " : ", e.strerror)
            exit()

        elif trimA == "Simple":
          trim.SimpleTrim(out_file, blank_out_file)
        elif trimA == "NRJ":
          trim.NRJTrim(outfile, blank_out_file)
        else:
          trim.NRJTrim(outfile, blank_out_file)

##################
#SFZ file writing
##################
    sfz.create_file(out_dir, grp, instru, oodict)
