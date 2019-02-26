import os
import re

#########################
# Sample Parser & Manager
#########################

#class for managing sample mapping
class sample:

  nttonb_dict = { "C":0,"Cs":1,"Db":1,"D":2,"Ds":3,"Eb":3,"E":4,"F":5,"Fs":6,"Gb":6,"G":7,"Gs":8,"Ab":8,"A":9,"As":10,"Bb":10,"B":11}
  nbtont_dict = { nb:nt for nt,nb in nttonb_dict.items()}

  def __init__(self, file, oodict):
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
      vel_range = 127 // len(sample_list[1]) + 1 #no rounding, take always upper value
      for smpl in sample_list[1]:
        smpl.lovel = val
        val += vel_range
        if val > 120 : val = 128 #adjust rounding
        smpl.hivel = val - 1


def fill_samplemap(sample_list, oodict):
  sample_map = dict()
  for i, smpl in enumerate(sample_list):
    smpl_class = sample(smpl, oodict)
    if smpl_class.key == -1:
      smpl_class.key = 48 + i
    if smpl_class.key in sample_map:
      sample_map[smpl_class.key].append(smpl_class)
    else:
      tmp = list()
      tmp.append(smpl_class)
      sample_map[smpl_class.key] = tmp
  return sample_map


##################
#SFZ file writing
##################
def create_file(out_dir, grp, instru, oodict):

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
          sample_map = fill_samplemap(sample_list, oodict)
          #sort main list (key) 
          #sample_map.sort(key = lambda sample_list : sample_list[0])
          #sort sub list (vel)
          for sample_list in sample_map.items():
            sample_list[1].sort(key = lambda sample : sample.vel)
          #fill key
          if instru["sort"] == "perc" or instru["sort"] == "perc_cut":
             fill_key_perc(sample_map)
          else:
             fill_key(sample_map)
          #fill vel
          fill_vel(sample_map)

          for sample_list in sample_map.items():
            for smpl in sample_list[1]:
              sfz_file.write("<region>\n")
              #if oodict["key"] == "phil":
              if instru["sort"] == "lgth" or instru["sort"] == "perc_cut":
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


