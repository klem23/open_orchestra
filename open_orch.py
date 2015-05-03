#!/usr/bin/env python

import os
import sys
import string
import zipfile
import urllib
import json

igroup = ["brass", "wood", "string", "perc"]

print "Using orchestra " + str(sys.argv[1])

#open json dict for corresponding orchestra
with open(str(sys.argv[1])) as data_file:    
  oodict = json.load(data_file)

  tmp_dir = oodict['temp directory']
  dwnld_dir = oodict['download directory']
  dwnld = False

#check temp and dwlnd directory
if not os.path.exists(tmp_dir):
	os.makedirs(tmp_dir)
if not os.path.exists(dwnld_dir):
	os.makedirs(dwnld_dir)

for grp in igroup : 
  if grp in oodict:
    for instru in oodict[grp] :
      #Create output dir for unzipped sample
      xtract_dir = tmp_dir + "/" + grp + "/" + instru["name"]
      if not os.path.exists(xtract_dir):
        os.makedirs(xtract_dir)
        dwnld = True

      #zip destination file
      dst_file = dwnld_dir + string.replace(os.path.basename(instru["url"]), "%20", "_")

      if dwnld :
        #Download
	print "Downloading " + oodict["input url"] + instru["url"]
        urllib.urlretrieve (oodict["input url"] + instru["url"], dst_file)

      #Extract
      print "Extract " + dst_file
      file_zip = zipfile.ZipFile(dst_file, "r")
      file_zip.extractall(xtract_dir)
      file_zip.close()

      #Transcode

      #Blank remover

      #SFZ file writing

