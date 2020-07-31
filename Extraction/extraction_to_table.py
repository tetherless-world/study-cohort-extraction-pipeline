#!/usr/bin/env python
# coding: utf-8

#very simple script for outputting a JSON PDF extraction as a plaintext table
#usage: extraction_to_table.py <json filename> [table filename]

import sys
import json

table_file = "./table_out.txt"

if(len(sys.argv) == 1):
    print("Usage: "+sys.argv[0]+" <json file> [output table file]")
    sys.exit()
if(len(sys.argv) >= 2):
    json_file = sys.argv[1]
if(len(sys.argv) >= 3):
    table_file = sys.argv[2]

row_header_width = 45
cell_width = 25

print("Opening \""+json_file+"\"...")

with open(json_file, "r") as read_file:
    data = json.load(read_file)
    
    #print data in tabular format
    with open(table_file, "w", encoding='utf-8') as write_file:
        
        for table_idx, table in enumerate(data["tables"]):

            num_rows = table["#-rows"]
            num_cols = table["#-cols"]

            write_file.write("TABLE {} ({}x{}):\n".format(table_idx+1, num_rows, num_cols))
            write_file.write("_"*((row_header_width+2)+(num_cols-1)*(cell_width+1))+"\n")

            row_format = "|{0[text]:<"+str(row_header_width)+"}|"
            for i in range(1,num_cols):
                row_format += "{"+str(i)+"[text]:>"+str(cell_width)+"}|"

            for row in table["data"]:
                write_file.write(row_format.format(*row)+"\n")
            write_file.write("\n\n")

print("Wrote table to \""+table_file+"\".")




