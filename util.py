from os.path import dirname, realpath, abspath, join
from os import walk

def abs_file_directory(file):
    dirname(realpath(file))

def absoluteFilePaths(directory):
   for dirpath, _,filenames in walk(directory):
       for f in filenames:
           yield abspath(join(dirpath, f))