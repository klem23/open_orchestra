#!/usr/bin/env python

import struct
import array




def Blank_Width():
  return 20

def Zero_reset():
  return 5

def Data_reset():
  return 10

def Data_match():
  return 100

#def Sensitivity():
#  return 0.05

#def NRJSensitivity():
#  return 0.1

def Window_size():
  return 1024

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


####################
#File management
####################

def trim_n_copy(infile, outfile, idx):
   try:
   #Prepare for copying
     with open(infile, 'rb') as audio_file:
       wh = audio_file.read(Wave_Header_Size())
       whd = struct.unpack(wave_header_fmt, wh)
       #print(whd[0])
       fh = audio_file.read(Fmt_Header_Size())
       fhd = struct.unpack(fmt_header_fmt, fh)

       audio_file.read(fhd[1] - Fmt_Header_Size() + 8)
       #if data is not PCM => extended header
       if fhd[2] != 1:
         facth = audio_file.read(8)
         facthd = struct.unpack("II", facth)
         factdatah = audio_file.read(facthd[1])
         print(facthd[1])

       audio_file.seek(0)
       with open(outfile, 'wb') as bo_file:
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



def SimpleTrim(infile, outfile, sensitivity=0.05):
  idx = getSimpleTrim(infile, sensitivity)
  trim_n_copy(infile, outfile, idx)


def NRJTrim(infile, outfile, sensitivity=0.05):
  idx = getNRJTrim(infile, sensitivity)
  trim_n_copy(infile, outfile, idx)







#############################################
#SILENCE DETECTION
#############################################
#SIMPLE AMP Threshold (noisegate)
def getSimpleTrim(outfile, sensitivity=0.05):

  print("Blank remover ", outfile)
  try:
    with open(outfile, 'rb') as audio_file:

      wh = audio_file.read(Wave_Header_Size())
      whd = struct.unpack(wave_header_fmt, wh)
      #print(whd[0])

      fh = audio_file.read(Fmt_Header_Size())
      fhd = struct.unpack(fmt_header_fmt, fh)
      print(fhd[1])

      #audio format
      print("format ", str(fhd[2]))
      #channels
      print("channels ", str(fhd[3]))
      #srate
      print("srate ", str(fhd[4]))
      #bitdepth
      print("bitdepth ", str(fhd[7]))

      if fhd[7] == 8:
        smpl_fmt = "B"
        smpl_size = 1
        smpl_treshold = sensitivity * 0xFF 
      elif fhd[7] == 16:
        smpl_fmt = "h"
        smpl_size = 2
        smpl_treshold = sensitivity * 0x7FFF
      elif fhd[7] == 24:
        smpl_fmt = "bbb"
        smpl_size = 3
        smpl_treshold = sensitivity * 0x7FFFFF
      elif fhd[7] == 32:
        smpl_fmt = "i"
        smpl_size = 4
        smpl_treshold = sensitivity * 0x7FFFFFFF

      print("treshold ", str(smpl_treshold))
      audio_file.read(fhd[1] - Fmt_Header_Size() + 8)

      #if data is not PCM => extended header
      if fhd[2] != 1:
        facth = audio_file.read(8)
        facthd = struct.unpack("II", facth)
        factdatah = audio_file.read(facthd[1])
        print(facthd[1])

      dh = audio_file.read(Data_Header_Size())
      dhd = struct.unpack(data_header_fmt, dh)
      print("data size ", str(dhd[1]))


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
        else:
          val = val_tmp[0]

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
      idx -= Data_match() * smpl_size
      idx -= idx % (fhd[3] * smpl_size)
      print("final idx :", str(idx))

    return idx

  except IOError :
    print("Error opening file, next ", outfile)
    return 0





#SILENCE catch by ENERGY Threshold
def getNRJTrim(outfile, sensitivity=0.05):
  print("NRJ Blank remover ", outfile)
  try:
    with open(outfile, 'rb') as audio_file:

      wh = audio_file.read(Wave_Header_Size())
      whd = struct.unpack(wave_header_fmt, wh)
      #print(whd[0])

      fh = audio_file.read(Fmt_Header_Size())
      fhd = struct.unpack(fmt_header_fmt, fh)
      print(fhd[1])

      #audio format
      print("format ", str(fhd[2]))
      #channels
      print("channels ", str(fhd[3]))
      #srate
      print("srate ", str(fhd[4]))
      #bitdepth
      print("bitdepth ", str(fhd[7]))

      if fhd[7] == 8:
        smpl_fmt = "B"
        smpl_size = 1
      elif fhd[7] == 16:
        smpl_fmt = "h"
        smpl_size = 2
      elif fhd[7] == 24:
        smpl_fmt = "bbb"
        smpl_size = 3
      elif fhd[7] == 32:
        smpl_fmt = "i"
        smpl_size = 4

      audio_file.read(fhd[1] - Fmt_Header_Size() + 8)

      #if data is not PCM => extended header
      if fhd[2] != 1:
        facth = audio_file.read(8)
        facthd = struct.unpack("II", facth)
        factdatah = audio_file.read(facthd[1])

      dh = audio_file.read(Data_Header_Size())
      dhd = struct.unpack(data_header_fmt, dh)
      print("data size ", str(dhd[1]))


      #get max amp and calcul blank remover treshold
      data = audio_file.read(smpl_size)
      idx = 0;
      accu = 0
      counter = 0
      average = 0
      nrjTab = []
      nrjMax = 0
      while data:
        val_tmp = struct.unpack(smpl_fmt, data)
        if smpl_size == 3:
          val = val_tmp[0] + val_tmp[1] * 0xFF + val_tmp[2] * 0xFFFF
          #val = val_tmp[0] + val_tmp[1] << 8 + val_tmp[2] << 16
        else:
          val = val_tmp[0]
        accu += val * val
        counter += 1
        if counter >= Window_size():
          nrjTab.append(accu)
          if accu > nrjMax:
            nrjMax = accu
          accu = 0
          counter = 0
        data = audio_file.read(smpl_size)

      i = 0
      while i < len(nrjTab) and nrjTab[i] < nrjMax * sensitivity :
        i += 1
      if i != len(nrjTab): 
        idx = i * Window_size() * smpl_size
        idx -= idx % (fhd[3] * smpl_size)


    print("final idx :", str(idx))
    return idx

  except IOError :
    print("Error opening file, next ", outfile)
    return 0


