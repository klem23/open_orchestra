#!/usr/bin/env python

import os
import sys
import subprocess
import string
import zipfile
import urllib
import json

instru_group = ["brass", "wood", "string", "perc"]

print "Using orchestra " + str(sys.argv[1])

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
#if not os.path.exists(out_dir):
#	os.makedirs(out_dir)

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

      #Create output dir for transcoded sample
      wav_sample_dir = tmp_dir + "/transcode/" + grp + "/" + instru["name"] + "/"
      if not os.path.exists(wav_sample_dir):
        os.makedirs(wav_sample_dir)

      #Transcode
      for infile in os.listdir(xtract_dir):
        print "transcoding : " + infile
	if (infile==".") or (infile=="..") :
	  break
        outfile = wav_sample_dir + os.path.splitext(infile)[0] + ".wav"
        try:
	  cmd = ["sox", xtract_dir + infile, outfile]
	  #print "command :" + str(cmd)
          subprocess.call(cmd)
        except OSError as e:
	  print "SOX programm for converting audio files has encounter a problem : " 
	  print "ERRNO " + str(e.errno) + " : " + e.strerror
	  exit()

      #Blank remover
        #with open(outfile) as audio_file: 
          #audio_file.lseek(WAVE_HEADER)
	  
	  #data = audio_file.fread(5)
	  #if data[4] == 0 && data[3]==0 etc
	  #pos = audio_file.lseek(0)
	  #wave_header -> new size
	  #copy file without zero
    

    #SFZ file writing
      sfz_file_name = out_dir + "/grp/" + instru["name"] + ".sfz"
      #with open(sfz_file_name) as sfz_file: 
	





  #Clean at end
  data_file.close()
