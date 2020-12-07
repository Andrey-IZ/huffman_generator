import os,sys,inspect
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.join(os.path.dirname(current_dir), 'app')
sys.path.insert(0, parent_dir) 
import huffman
