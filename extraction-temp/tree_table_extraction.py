#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Accepts a JSON PDF extraction and outputs a tree table intermediate structure (also in JSON).

Usage: extraction_to_table.py <json filename> [table filename] [-v]
If table filename is not provided, one is generated based on the name of the JSON and the current time.
The -v option will create a plaintext visualization of the table in [table filename].

"""

import sys
import json
import datetime
import copy
import warnings
import argparse
import os

# follows x.y.z format
# x refers to stage in process (e.g. stage 0 refers to tree table json)
# y refers to overall structure version (should be incremented if structure is changed in a major way)
# z refers to iteration of structure (should be incremented after minor change that preserves backwards compatibility)
CURRENT_VERSION_NUM = "0.0.2"

# max filename + path length for windows
MAX_FNAME = 259

def box_inside_box(inner,outer):
  """Return true if the inner bbox is inside or equal to the outer bbox.
  
  Parameters:
    inner (list): List of floats for inner bounding box of form [x0,y0,x1,y1]
    outer (list): List of floats for outer bounding box of form [x0,y0,x1,y1]
  
  Returns:
    bool: Whether inner is insider outer
  """
  if outer[0] <= inner[0] and outer[1] <= inner[1] and inner[2] <= outer[2] and inner[3] <= outer[3]:
      return True
  return False

def get_font(bbox, old_table):
  """Get the text segments and their fonts from old_table matching bbox.
  
  Parameters:
    bbox (list): List of floats for bounding box of form [x0,y0,x1,y1]
    old_table (dict): Table from PDF Extraction JSON to search
  
  Returns:
    list: List of [Text, Font] string lists, where Text has a bounding box
    within bbox and font Font.
  """
  # this could be made more efficient as cells are arranged in a rough order
  fontsFound = []
  for cell in old_table["cells"]["data"]:
      if box_inside_box(cell[0:4],bbox[0:4],):
          fontsFound.append([cell[5],cell[4]])
  if len(fontsFound) == 0:
      warnings.warn("Cell not found for ["+("".join([str(i)+"," for i in bbox]))+"]")
  return fontsFound

def make_cell(old_cell, old_table):
  """Make a cell of the new format (tree table) corresponding to old_cell.
  
  Parameters:
    old_cell (dict): Cell from PDF Extraction JSON
    old_table (dict): Table from PDF Extraction JSON containing old_cell
    
  Returns:
    dict: Cell with properties "bbox", "spans", "text", "type", "table_num", and "font" 
  """
  new_cell = copy.deepcopy(old_cell)
  bbox = new_cell["bbox"]
  if(bbox is not None):
      new_cell["fonts"] = get_font(bbox, old_table)
  else:
      new_cell["fonts"] = []
  new_cell["table_num"] = old_table["table_num"]
  return new_cell

def get_indent(row):
  """Get indent of row's first cell (that is, left edge of bounding box in px).
  
  Parameters:
    row (list): List of PDF Extraction-type cells
    
  Returns:
    float
  """
  if len(row) > 0 and row[0]["bbox"] is not None:
      return row[0]["bbox"][0]
  else:
      return 0.0

def make_tree_tables(extraction):
  """Make the tree table intermediate data structure from the loaded PDF extraction.
    
  Parameters:
    extraction (dict) : the PDF JSON extraction (acquired via load_extraction)

  Returns:
    dict: the intermediate data structure, with the tree tables in dict["tables"]
  """
  # make new dict for root object
  # copy over relevant info

  new_data = {"_version": CURRENT_VERSION_NUM}

  for key, value in extraction.items():
      if key != "tables":
          new_data[key] = copy.deepcopy(value)
  new_data["tables"] = []

  for table_idx, old_table in enumerate(extraction["tables"]):

      # keep track of table_idx
      old_table["table_num"] = table_idx
        
      if len(old_table["data"]) == 0:
          continue

      new_table = {"fields":[],"records":[]}
      new_data["tables"].append(new_table)

      # TODO: go over entire table once to identify most common indentation levels
      
      #indent_range is intended as the +/- value to be added to an indent offset to determine the range of values that fall within that indentation level
      indent_range = 1.0;
      
      # determine column names
      new_table["fields"] = []
      for old_cell in old_table["data"][0]:
          new_table["fields"].append(make_cell(old_cell, old_table))
          
      # stack keeps track of nested tables
      stack = [(new_table, get_indent(old_table["data"][0]))]
      
      for old_row in old_table["data"][1:]:
          
          # make a new table for this row
          current = {"fields":[],"records":[]}
          
          # find fields
          for old_cell in old_row:
              current["fields"].append(make_cell(old_cell, old_table))
          
          c_indent = get_indent(old_row)
          # go backwards through stack and find parent
          for parent,p_indent in reversed(stack):
              
              # if we have reached the root element, we know we have reached a parent
              if len(stack) == 1:
                  break
              
              # if p_indent is less than c_indent, it is a parent
              if p_indent < c_indent - indent_range:
                  break
              
              # if p_indent is roughly equal to c_indent
              if p_indent > c_indent - indent_range and p_indent < c_indent + indent_range:
                  # if parent is bold and current is not, it is a parent
                  if len(parent["fields"][0]["fonts"]) != 0 and len(current["fields"][0]["fonts"]) != 0:
                      
                      # number of bold characters, or all characters
                      bold_parent = 0
                      all_parent = 0
                      bold_current = 0
                      all_current = 0
                      for text,font in parent["fields"][0]["fonts"]:
                            font = font.lower()
                            if("bold" in font or "semi" in font or "demi" in font or "heavy" in font or "black" in font):
                                bold_parent += len(text)
                            all_parent += len(text)
                      for text,font in current["fields"][0]["fonts"]:
                            font = font.lower()
                            if("bold" in font or "semi" in font or "demi" in font or "heavy" in font or "black" in font):
                                bold_current+= len(text)
                            all_current+= len(text)
                      # ratio of bold characters / all characters
                      parent_ratio = float(bold_parent)/float(all_parent)
                      current_ratio = float(bold_current)/float(all_parent)
                      
                      # if parent is at least 50% bold, but current is not: parent is a parent
                      if parent_ratio >= 0.5 and current_ratio < 0.5:
                          break
                  
              # if p_indent is greater or roughly equal to c_indent, it is not a parent
              # remove parent from stack
              stack.pop()
          
          # apply child to parent, stack
          parent["records"].append(current)
          stack.append((current,c_indent))
                  
                                            
  return new_data

def get_col_widths(table, tab_width=2, tab_level=0, col_padding=0):
  """Recursively get the list of max number of characters of each column in table.

  Parameters:
    table (dict): The table to check (has "fields" and "records" properties) 
    tab_width (int): The amount of space to leave for tabs. By default, 2.
    tab_level (int): The number of tables this table is nested within. By default, 0.
    col_padding (int): How much space to pad columns with. By default, 0.
  
  Returns:
    list: List of ints corresponding to the maximum number of characters per table column.
  """
  col_widths = []
  for cell in table["fields"]:
      col_widths.append(len(cell["text"])+col_padding)
  col_widths[0] += tab_width * tab_level
  
  # take max of this col_widths or col_widths returned by recursing on children
  for row in table["records"]:
      child_widths = get_col_widths(row, tab_width, tab_level + 1, col_padding)
      for i in range(0,len(col_widths)):
          col_widths[i] = max(col_widths[i],child_widths[i])
  
  return col_widths

def print_table(table, col_widths, write_file, layer=0):
  """Recursively print a single table to write_file.
  
  Parameters:
    table (dict): The table to print (has "fields" and "records" properties)
    col_widths (list): A list of ints corresponding to number of characters per column.
    write_file (file): A file to write to.
    layer (int): How many tables this table is nested within. By default, 0.
  """
  # Not a parameter as tab_width is always 2 when " |" is used for tabs.
  tab_width = 2
  
  # Subtract tab width from the first column of a table of any layer. Not multiplied as
  # col_widths is provided as a parameter when recursing.
  num_cols = len(col_widths)
  col_widths = copy.copy(col_widths)
  if layer > 0: col_widths[0] -= tab_width
  
  # horiz_line is reused several times when printing a line, with box drawing chars replaced
  horiz_line = "│ "*layer+ "┌"
  for i,col in enumerate(col_widths):
      horiz_line+="─"*(col_widths[i])
      if i < len(col_widths)-1:
          if layer > 0: horiz_line+="┼"
          else: horiz_line+="┬"
      else:
          if layer > 0: horiz_line+="┤\n"
          else: horiz_line+="┐\n"
  write_file.write(horiz_line)

  # row_format is used whenever cells are printed
  row_format = "│"+" │"*layer
  for i in range(0,num_cols):
      row_format += "{"+str(i)+"[text]:>"+str(col_widths[i])+"}│"
  row_format = row_format.replace('>','<',1)

  write_file.write(row_format.format(*table["fields"])+"\n")
  
  # recurse and print any children this table might have
  if len(table["records"]) > 0:
      write_file.write(horiz_line.replace('┐','┤').replace('┌','├').replace('┬','┼'))
      for subtable in table["records"]:
          print_table(subtable, col_widths, write_file, layer+1)

  write_file.write(horiz_line.replace('┐','┘').replace('┌','└').replace('┬','┴'))

def print_tree_tables(tree_tables, filename):
  """Print the tree tables in a plaintext visualization.
  
  Parameters:
    tree_tables (dict): The intermediate data structure, with the tree tables in dict["tables"]
    filename (str): The name of the file to print the tree tables visualization to.
    
  Returns:
    dict: The unchanged tree_tables dictionary.
  """
  with open(filename, 'w', encoding='utf-8') as write_file:
      
      for table_idx, table in enumerate(tree_tables["tables"]):

          num_rows = len(table["fields"])
          num_cols = len(table["records"])
          
          # recursively get max width of each column
          col_widths = [0] * num_cols
          col_widths = get_col_widths(table)
          
          # table header
          write_file.write("\nTABLE {} ({}x{}):\n".format(table_idx+1, num_rows, num_cols))
          
          # recursively print each table
          print_table(table, col_widths, write_file, 0)
  
  print("Saved plaintext visualization of tree tables to "+filename+"\n")
  
  return tree_tables

def save_tree_tables(tree_tables, filename):
  """Save the intermediate data structure as a JSON file.
  
  Parameters:
    tree_tables (dict): The intermediate data structure, with the tree tables in dict["tables"]
    filename (str): The name of the file to save the tree tables to.
    
  Returns:
    dict: The unchanged tree_tables dictionary.
  """
  with open(filename, 'w', encoding='utf-8') as save_file:
      json.dump(tree_tables, save_file, indent=2)
  
  print("Saved tree tables to "+filename+"\n")
  
  return tree_tables

def load_extraction(json_file):
  """Load data from a PDF Extraction JSON file.

  Parameters:
    json_file (str): Filename, incl. path, to the PDF extraction JSON file

  Returns: 
    dict: Dictionary representation of the loaded object.
  """
  with open(json_file, "r") as read_file:
      extraction = json.load(read_file)
  
  print("\nLoaded extraction from "+json_file+"\n")
  
  return extraction
    
def gen_filepath(input_fp, prefix, ext, max_length):
  """Generate a filepath of the form abs_dir(input_fp)+\+prefix+base_name(input_fp)+_+time+ext
  
  Parameters:
    input_fp (str): A valid filepath to use to generate the new name
    Prefix (str): Prefix for the new name (e.g "Intermediate_Tree_Table_")
    ext (str): File extention, not appended if input_fp already has extention ext
    max_length (int): Will trim the output filepath to have at most this many characters
  
  Returns:
    str: The resulting filepath
  """
  # use abspath to account for max filename issues
  dir = os.path.dirname(os.path.abspath(input_fp))+"\\"
  fn = os.path.basename(os.path.abspath(input_fp))
  
  # don't write filepath.ext.ext
  if (fn.rfind(ext) > -1):
    fn = fn[0:fn.rfind(ext)]
    
  # label with current time, trim milliseconds
  time = str(datetime.datetime.now()).replace(" ","_").replace(":",".")
  time = "_"+time[0:time.rfind(".")]
  
  output_fp = dir+prefix+fn+time+ext
  
  # avoid max filename issues on windows (4 character buffer for .txt of v_file)
  fn_chars_to_trim = len(output_fp) - max_length
  if fn_chars_to_trim > 0:
    output_fp = dir+prefix+fn[0:len(fn)-fn_chars_to_trim]+time+ext
  
  return output_fp
  
def main():
  """Load the PDF extraction, generate tree tables, and write those tree tables to a file.
  
  The path/filename of the input file, the (optional) path/filename of the output file,
  and the (optional) visualization option -v are provided via sys.argv
  """
  parser = argparse.ArgumentParser(description="Takes a JSON PDF extraction and turns it into a JSON tree table.")

  parser.add_argument('input_file', help='JSON file extracted from PDF')
  parser.add_argument('output_file', help='Name of tree table JSON to create, if not provided will be generated based on input_file and time', nargs='?', default=None)
  parser.add_argument('-v', '--visualization', help='If provided, creates a plaintext visualization of the table in [output_file].txt', action='store_true')
  
  args = parser.parse_args()
  
  input_file = args.input_file
  output_file = args.output_file
  
  # generate output filename if none provided
  if output_file is None:
    # leave a 4 character buffer for v_file
    output_file = gen_filepath(input_file, "Intermediate_Tree_Table_", ".json", MAX_FNAME - 4)

  tree_tables = save_tree_tables(make_tree_tables(load_extraction(input_file)), output_file)
  
  if args.visualization:
      v_file = output_file+".txt"
      print_tree_tables(tree_tables, v_file)

if __name__ == "__main__":
    
    main()


