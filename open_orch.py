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

def Blank_Width():
  return 20

#function to sort sample list
def sample_list_key(filename):
  elem = string.split(filename, oodict["splitter"])
  for tag in elem:
    if re.match("[A-G][0-9]", tag):
      char_key = list(tag)
      key = char_key[1] + char_key[0] + "d"
    if re.match("[A-G][b-s][0-9]", tag):
      char_key = list(tag)
      key = char_key[2] + char_key[0] + char_key[1]

  return key


wave_header_fmt = "III"
fmt_header_fmt = "HHIIHH"
data_header_fmt = "II"

def Wave_Header_Size():
  return 12

def Fmt_Header_Size():
  return 8

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
            fhd = struct.unpack("II", fh)

            print fhd[1]
	    fmth = audio_file.read(16)
            fmthd = struct.unpack(fmt_header_fmt, fmth)

            #audio format
            print "format " + str(fmthd[0])
            #channels
            print "channels " + str(fmthd[1])
            #srate
            print "srate " + str(fmthd[2])
            #bitdepth
            print "bitdepth " + str(fmthd[5])

            if fmthd[5] == 8:
              smpl_fmt = "B"
              smpl_size = 1
            elif fmthd[5] == 16:
              print "yopypi"
              smpl_fmt = "H"
              smpl_size = 2 
            elif fmthd[5] == 24:
              smpl_fmt = "BBB"
              smpl_size = 3

            fmth2 = audio_file.read(fhd[1] - 16)

            #if data is not PCM => extended header
            if fmthd[0] != 1:
              facth = audio_file.read(8)
              facthd = struct.unpack("II", facth)
              factdatah = audio_file.read(facthd[1])	
          

            dh = audio_file.read(Data_Header_Size())
            dhd = struct.unpack(data_header_fmt, dh)
            print "data size " + str(dhd[1])

          #audio_file.lseek(WAVE_HEADER)
	    #audio_file.seek(44)
	    data = audio_file.read(smpl_size)
            idx = 0;
            while data:
	      val = struct.unpack(smpl_fmt, data)[0]
	      if val != 0:
		found = False
                #if not 0 in data[1] and not 0 in data[2] and not 0 in data[3] and not 0 in data[4]:
		for i in range(0, Blank_Width() - 1):
	          val = struct.unpack(smpl_fmt, audio_file.read(smpl_size))[0]
                  if val == 0:
                   found = True
                   break
                if not found:
                  print "stop :" + str(idx)
                  break
                else:
                  idx += smpl_size * Blank_Width()
          
	      #data = audio_file.read(Blank_Width())
	      data = audio_file.read(smpl_size)
              idx += smpl_size
            print "final idx :" + str(idx)


          #Prepare for copying
            blank_out_file =  sfz_sample_dir + os.path.splitext(infile)[0] + ".wav"
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
              bo_file.write(audio_file.read(fhd[1] + 8))
              #if data is not PCM => extended header
              if fmthd[0] != 1:
                facth = audio_file.read(8)
                #facthd = struct.unpack("II", facth)
                factdatah = audio_file.read(facthd[1])

          
              #DATA 
              bo_file.write(audio_file.read(4))
              bo_file.write(struct.pack("I", struct.unpack("I", audio_file.read(4))[0] - idx))
              audio_file.seek(idx, 1)
              bo_file.write(audio_file.read())


	  #wave_header -> new size
	  #copy file without zero
        except IOError :
          print "Error opening file, next"
          continue

##################
#SFZ file writing
##################

      sfz_file_name = out_dir + "/" + grp + "/" + instru["name"] + ".sfz"
      print "Create SFZ file : " + sfz_file_name
      with open(sfz_file_name, 'w') as sfz_file: 
        sfz_file.write("// ----------------------\n")
        sfz_file.write("//  Open Orchestra\n")
        sfz_file.write("// ----------------------\n")
        sfz_file.write("//  " + oodict["orchestra name"] + "\n")
        sfz_file.write("// ---------------------- \n")
        sfz_file.write("//  " +instru["name"] + "\n")
        sfz_file.write("// ---------------------- \n\n\n\n")


        sfz_file.write("<group>\n")
        sfz_file.write("\n")
	
        sample_list = os.listdir(out_dir + "/" + grp + "/" + instru["name"] + "/")
        sample_list.sort(key = sample_list_key)
        for audiofile in sample_list :	
          sfz_file.write("<region>\n")
          sfz_file.write("sample=" + grp + "/" + instru["name"] + "/" + audiofile + "\n")
          elem = string.split(audiofile, oodict["splitter"])
          for tag in elem:
	    if re.match("[A-G][0-9]", tag) or re.match("[A-G][b-s][0-9]", tag) :
              note = tag
              sfz_file.write("lokey=" + note + "\n")
              sfz_file.write("hikey=" + note + "\n")
              sfz_file.write("pitch_keycenter=" + note +"\n")
              break

          sfz_file.write("\n")

