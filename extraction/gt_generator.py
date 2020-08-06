from tkinter import *
from tkinter import ttk
import tkinter as tk
from tree_table_extraction import *
import datetime
import json
from rdflib import Graph, URIRef
import rdflib

# objects:

# metarow:
#  --old_idx
#  --new_idx
#  --is_valid
#  --header_text
#  --row_text

# metacol:
#  --old_idx
#  --new_idx
#  --is_valid
#  --header_text

# metatable:
#  --old_idx
#  --new_idx
#  --is_valid

# metacell:
#  --is_valid 
#  --cell_text

normal_color = "#FAFAFA"
skipped_color = "#C3C3C3"

class Table_Inspector:
    
    # data, filename, meta_filename
    
    # mode
    
    # cells,rows,cols,tbllabel, focus, curr_table_idx
    
    # root, 
    
    def __init__(self, intermediate_structure, filename):
        
        self.data = intermediate_structure
        if (not filename.endswith(".json")): self.meta_filename = "./meta."+filename+".json"
        else:                                          self.meta_filename = "./meta."+filename
        self.filename = filename
        
        self.mode = "META"
        self.elem_index = 0
        
        self.root = Tk()
        self.root.geometry("1000x750+500+0")
        
        self.skipped = {"cell":[],"row":[],"col":[],"table":[]}
        self.added = 0
        
        self.make_filename_entry()
        
        # tell tables their original indices
        # and flatten
        self.flat_tables = []
        for table in self.data["tables"]:
            flat_table = self.prepare_table(table,0)
            self.flat_tables.append(flat_table)
        
        self.current_table_idx = 0
        self.top_frame = None
        self.bottom_frame = None
        self.update_window(self.current_table_idx)
        
        self.make_buttons()
        
        self.set_focus(self.current_table_idx,None,"table")
        
        self.root.mainloop()
        
    def make_filename_entry(self):
        
        # make display frame
        self.fn_entry_frame = LabelFrame(self.root)
        self.fn_entry_label = StringVar()
        FnEntryLabel = Label(self.fn_entry_frame, textvariable=self.fn_entry_label)
        self.fn_entry_label.set("Filepath to save to:")
        self.fn_entry_contents = StringVar()
        self.fn_text_field = Entry(self.fn_entry_frame, textvariable=self.fn_entry_contents)
        self.fn_text_field.bind('<Return>', self.save)
        
        #meta fn 
        self.fn_entry_contents.set(self.meta_filename)
        
        SaveButton = Button(self.fn_entry_frame, text ="Save", command = self.save)
        
        # pack
        self.fn_entry_frame.pack(side=TOP, fill="x")
        FnEntryLabel.pack(side=LEFT)
        self.fn_text_field.pack(side=LEFT, fill="x", expand=True)
        SaveButton.pack(side=LEFT)
        
    def change_mode_gt(self):
        self.mode = "GT"
        
        g = Graph()
        self.g = g
        
        # ensure correct prefixes
        g.namespace_manager.bind('sio', URIRef("http://semanticscience.org/resource/"))
        g.namespace_manager.bind('sco', URIRef("https://idea.tw.rpi.edu/projects/heals/studycohort/"))
        g.namespace_manager.bind('sco-i', URIRef("https://idea.tw.rpi.edu/projects/heals/studycohort_individuals/"))
        g.namespace_manager.bind('owl', URIRef("http://www.w3.org/2002/07/owl#"))
        
        self.elem_index = 0
        
        # Iterate through column headers
        # Look for cell["column"] : these are lists of top-level features
        for table in self.flat_tables:
            for cell in table[0]["fields"]:
                if "column" in cell:
                    for f in cell["column"]:  
            # translate these features to RDF
                        f.translate(g)
                
        #gra_fn = "./gra."+"temp"+".ttl"
        #g.serialize(gra_fn,format='turtle')
        #print("Saved KG serialization to ",gra_fn,"\n")
        
        # use a SPARQL query or two to identify ALL bnode-hasvalue*-<x> that originate from some cell
        # *remember has-min-value and has-max-value
        
        qres = g.query("""
            prefix owl: <http://www.w3.org/2002/07/owl#> 
            prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
            prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            prefix sco: <https://idea.tw.rpi.edu/projects/heals/studycohort/> 
            prefix sio: <http://semanticscience.org/resource/> 


            select distinct ?measure ?property ?value ?col ?row ?table ?att_label ?acol ?arow ?atable {
              ?bnode ?property ?value.
              ?bnode a ?measure.
              ?bnode sco:colIndex ?col.
              ?bnode sco:rowIndex ?row.
              ?bnode sco:tableIndex ?table.
              OPTIONAL { 
                ?att sio:hasAttribute ?bnode.
                ?att rdfs:hasLabel ?att_label.
                ?att sco:colIndex ?acol.
                ?att sco:rowIndex ?arow.
                ?att sco:tableIndex ?atable.
              }
              FILTER ((?property = sio:hasValue || ?property = sio:hasMinValue || ?property = sio:hasMaxValue) )
            }
            
        """)
        
        # store pointers to these bnodes in the appropriate cell
        
        print(len(qres))
        for row in qres:
            #print("%s %s %s %s %s %s %s" % row)
            
            # match to correct indices (new row idx instead of old)
            tab_idx = int(row["table"])
            old_row_idx = int(row["row"])
            col_idx = int(row['col'])
            row_idx = self.meta_object["tables"][tab_idx]["row_mappings"][old_row_idx]
            
            # and store pointers in each cell to the data
            cell = self.flat_tables[tab_idx][row_idx]["fields"][col_idx]
            
            row_object = {}
            for k in ["measure", "property", "value", "col", "row", "table", "att_label" ,"acol", "atable"]:
                row_object[k] = row[k]
            
            if(row["arow"] is not None):
                atab_idx = int(row["atable"])
                old_arow_idx = int(row["arow"])
                row_object["arow"] = self.meta_object["tables"][atab_idx]["row_mappings"][old_arow_idx]
            else:
                row_object["arow"] = None
            
            cell["data_items"].append(row_object)
        
        # then, run update_window, but create an additional panel which shows the 
        #  1. value (bnode-hasvalue-<x>)
        #   (1a) property
        #  2. type (bnode-type-<meas_type>)
        #   (2a)label/other triples
        #  4. attribute parents (<att>-hasAttribute-bnode)
        #   (4a) attribute parents origin cell, label information (even if skipped)
        # alternatively, you could show all triples originating from this bnode
        
        self.make_buttons()
        
        self.update_window(0)
        
        self.set_focus(0,None,"table")
        
        # the idea though, is you scroll through each data item (<x>) one at a time
        # and can modify 1,2,4 as needed
        
        # additionally, you can add your own triples, or remove the ones there
        
    def update_window(self, table_idx):
        
        self.current_table_idx = table_idx
        
        if self.top_frame is not None:
            self.grid_frame.scrollbar_x.destroy()
            self.top_frame.destroy()
        
        #table = self.data["tables"][table_idx]
        
        #num_cols = len(table["fields"])
        #num_rows = get_num_rows(table)
        table = self.flat_tables[table_idx]
        num_rows = len(table)
        num_cols = len(table[0]["fields"])
                
        self.cells = [[None for i in range(num_cols)] for j in range(num_rows)] 
        self.rows = [None for i in range(num_rows)]
        self.cols = [None for i in range(num_cols)]
        
        title = "Table "+str(table_idx+1)+"/"+str(len(self.data["tables"]))+": ("+str(num_cols)+"x"+str(num_rows)+")"
        self.top_frame = LabelFrame(self.root, text=title)
        
        self.grid_frame = ScrollableFrame(self.top_frame, self.root)
        
        # make table button for grid
        tbl_button_frame = LabelFrame(self.grid_frame.scrollable_frame)
        self.tbllabel = Button(tbl_button_frame, text="[T"+str(table_idx)+"]", command= lambda : self.set_focus(table_idx,None,"table"), bg ="#FAFAFA")
        tbl_button_frame.grid(row=0, column=0)
        tbl_button_frame.rowconfigure(0, weight=1)
        tbl_button_frame.columnconfigure(0, weight=1)
        tbl_button_frame.grid(sticky=N+E+W+S)
        self.tbllabel.pack()
        
        # make col buttons for grid
        for col_index in range(0,num_cols):
            col_frame = LabelFrame(self.grid_frame.scrollable_frame)
            collabel = Button(col_frame, text="[C"+str(col_index)+"]", bg="#FAFAFA",command= lambda c=col_index: self.set_focus(None,c,"col") )#relief="groove"
            col_frame.grid(row=0, column=col_index+1)
            col_frame.rowconfigure(0, weight=1)
            col_frame.columnconfigure(col_index+1, weight=1)
            col_frame.grid(sticky=N+E+W+S)
            collabel.pack()
            self.cols[col_index] = collabel
        
        # make grid
        #self.add_to_grid(table, self.grid_frame.scrollable_frame, 0)
        self.draw_table(table)
        
        # pack
        self.top_frame.pack(side=TOP, fill="both", expand=True)
        self.grid_frame.scrollbar_x.pack(fill="x")
        self.grid_frame.pack(side=LEFT, fill="both", expand=True)
        
    def make_buttons(self):
        
        if self.bottom_frame is not None:
            self.bottom_frame.destroy()
        
        # make buttons
        self.bottom_frame = LabelFrame(self.root)
        AddBeforeButton = Button(self.bottom_frame, text ="Add Before", command = self.add_before)
        AddAfterButton = Button(self.bottom_frame, text ="Add After", command = self.add_after)
        RemoveButton = Button(self.bottom_frame, text ="Remove", command = self.remove)
        SkipButton = Button(self.bottom_frame, text ="Skip", command = self.skip)
        PrevButton = Button(self.bottom_frame, text ="Previous", command = self.prev)
        NextButton = Button(self.bottom_frame, text ="Next", command = self.next_focus)
        
        # make display frame
        self.entry_frame = LabelFrame(self.bottom_frame)
        self.entry_label = StringVar()
        EntryLabel = Label(self.entry_frame, textvariable=self.entry_label)
        self.entry_label.set("Enter:")
        self.entry_contents = StringVar()
        self.text_field = Entry(self.entry_frame, textvariable=self.entry_contents)
        self.text_field.bind('<Return>', self.submit)
        SubmitButton = Button(self.entry_frame, text ="Submit", command = self.submit)
        
        if (self.mode == "GT"):
            # create an additional panel which shows the 
            #  1. value (bnode-hasvalue-<x>)
            #   (1a) property
            #  2. type (bnode-type-<meas_type>)
            #   (2a)label/other triples
            #  4. attribute parents (<att>-hasAttribute-bnode)
            #   (4a) attribute parents origin cell, label information (even if skipped)
            # alternatively, you could show all triples originating from this bnode
            self.triple_frame = Frame(self.bottom_frame)
            
            self.measure = StringVar()
            self.property = StringVar()
            self.value = StringVar()
            self.att_label = StringVar()
            self.att_row = StringVar()
            self.att_col = StringVar()
            self.att_table = StringVar()
            
            meas_entry = Entry(self.triple_frame, textvariable=self.measure)
            prop_entry = Entry(self.triple_frame, textvariable=self.property)
            val_entry = Entry(self.triple_frame, textvariable=self.value)
            att_lab_entry = Entry(self.triple_frame, textvariable=self.att_label)
            att_row_entry = Entry(self.triple_frame, textvariable=self.att_row)
            att_col_entry = Entry(self.triple_frame, textvariable=self.att_col)
            att_tbl_entry = Entry(self.triple_frame, textvariable=self.att_table)
            
            meas_entry.bind('<Return>', self.submit)
            prop_entry.bind('<Return>', self.submit)
            val_entry.bind('<Return>', self.submit)
            att_lab_entry.bind('<Return>', self.submit)
            att_row_entry.bind('<Return>', self.submit)
            att_col_entry.bind('<Return>', self.submit)
            att_tbl_entry.bind('<Return>', self.submit)
        
        # repack
        
        self.bottom_frame.pack(side=BOTTOM, fill="x")
        
        if(self.mode == "GT"):
            self.triple_frame.pack(side=TOP,fill="x", expand=True)
            meas_entry.pack(side=LEFT, fill="x", expand=True)
            prop_entry.pack(side=LEFT, fill="x", expand=True)
            val_entry.pack(side=LEFT, fill="x")
            att_lab_entry.pack(side=LEFT, fill="x", expand=True)
            att_row_entry.pack(side=LEFT, fill="x")
            #att_col_entry.pack(side=LEFT, fill="x")
            #att_tbl_entry.pack(side=LEFT, fill="x")
        
        self.entry_frame.pack(side=TOP, fill="x", expand=True)
        EntryLabel.pack(side=LEFT)
        self.text_field.pack(side=LEFT, fill="x", expand=True)
        SubmitButton.pack(side=LEFT)
        
        AddBeforeButton.pack(side=LEFT)
        AddAfterButton.pack(side=LEFT)
        RemoveButton.pack(side=LEFT)
        SkipButton.pack(side=LEFT)
        NextButton.pack(side=RIGHT)
        PrevButton.pack(side=RIGHT)
    
    def draw_table(self,flat_table):
        
        grid_frame = self.grid_frame.scrollable_frame
        
        for row_index, row_object in enumerate(flat_table):
            
            # do row button
            row_frame = LabelFrame(grid_frame)
            rowlabel = Button(row_frame, text="[R"+str(row_index)+"]", bg="#FAFAFA",command= lambda r=row_index:self.set_focus(r,None,"row"))
            row_frame.grid(row=row_index+1, column=0)
            row_frame.rowconfigure(row_index+1, weight=1)
            row_frame.columnconfigure(0, weight=1)
            row_frame.grid(sticky=N+E+W+S)
            rowlabel.pack()
            self.rows[row_index] = rowlabel
            
            for col_index, cell in enumerate(row_object["fields"]):
                
                frame = LabelFrame(grid_frame)
                if self.mode == "META":
                    callback = lambda c=col_index,r=row_index: self.set_focus(r,c,"cell")
                else:
                    callback = lambda c=col_index,r=row_index: self.set_focus(r,c,"element",0)
                label = Button(frame, text=cell["new_text"], bg="#FAFAFA",command= callback)
                frame.grid(row=row_index+1, column=col_index+1)
                frame.rowconfigure(row_index+1, weight=1)
                frame.columnconfigure(col_index+1, weight=1)
                frame.grid(sticky=N+E+W+S)
                label.pack(fill="both", expand=True)
                self.cells[row_index][col_index] = label
                
    
    # old one (uses row indices)
    def add_to_grid(self, table, grid_frame, row_index):
        
        # do row button
        row_frame = LabelFrame(grid_frame)
        rowlabel = Button(row_frame, text="[R"+str(row_index)+"]", bg="#FAFAFA",command= lambda : self.set_focus(row_index,None,"row") )#relief="groove"
        row_frame.grid(row=row_index+1, column=0)
        row_frame.rowconfigure(row_index+1, weight=1)
        row_frame.columnconfigure(0, weight=1)
        row_frame.grid(sticky=N+E+W+S)
        rowlabel.pack()
        self.rows[row_index] = rowlabel
        
        for col_index, cell in enumerate(table["fields"]):
            
            frame = LabelFrame(grid_frame)
            label = Button(frame, text=cell["new_text"], bg="#FAFAFA",command= lambda c=col_index: self.set_focus(row_index,c,"cell"))
            frame.grid(row=row_index+1, column=col_index+1)
            frame.rowconfigure(row_index+1, weight=1)
            frame.columnconfigure(col_index+1, weight=1)
            frame.grid(sticky=N+E+W+S)
            label.pack(fill="both", expand=True)
            self.cells[row_index][col_index] = label
        
        prev_rows=1
        for i, record in enumerate(table["records"]):
            self.add_to_grid(record, grid_frame, row_index+prev_rows)
            prev_rows += get_num_rows(record)
        
            
    def add_before(self):
        row_index,col_index,meta_object = self.focus
        
        if meta_object == "row":
            self.add_row(0)
        
    def add_after(self):
        row_index,col_index,meta_object = self.focus
        
        if meta_object == "row":
            self.add_row(1)
            
    def add_row(self, distance):
        row_index,col_index,meta_object = self.focus
        
        if meta_object == "row":
            self.added +=1
            new_row = {"old_idx":-1*self.added,"old_text":"","new_text":"","fields":[],"records":[]}
            # cells have "bbox", "spans", "text", "type", "table_num", and "font"
            for sample_cell in self.flat_tables[self.current_table_idx][0]["fields"]:
                new_cell = {"bbox":[0,0,0,0],"spans":[row_index,col_index],"text":"","new_text":"","type":"","table_num":self.current_table_idx,"font":""}
                new_row["fields"].append(new_cell)

            # add the new row after the current row
            self.flat_tables[self.current_table_idx].insert(row_index+distance,new_row)

            self.update_window(self.current_table_idx)

            self.set_focus(row_index+distance,col_index,meta_object)
        
    def remove(self):
        row_index,col_index,meta_object = self.focus
        if self.mode=="GT" and meta_object == "element":
            cell = self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]
            del cell["data_items"][self.elem_index]
            
            self.elem_index-=1
            if self.elem_index < 0:
                self.elem_index = 0
            self.next_focus()
        
    def skip(self):
        row_index,col_index,meta_object = self.focus
        
        if meta_object == "table":
            if self.current_table_idx in self.skipped["table"]:
                self.skipped["table"].remove(self.current_table_idx)
            else:
                self.skipped["table"].append(self.current_table_idx)
        elif meta_object == "col":
            if col_index in self.skipped["col"]:
                self.skipped["col"].remove(col_index)
            else:
                self.skipped["col"].append(col_index)
        elif meta_object == "row":
            old_idx = self.get_old_row_idx(row_index, self.current_table_idx)
            if old_idx in self.skipped["row"]:
                self.skipped["row"].remove(old_idx)
            else:
                self.skipped["row"].append(old_idx)
        elif meta_object == "cell":
            old_idx = self.get_old_row_idx(row_index, self.current_table_idx)
            if (old_idx,col_index) in self.skipped["cell"]:
                self.skipped["cell"].remove((old_idx,col_index))
            else:
                self.skipped["cell"].append((old_idx,col_index))
                
                
        self.next_focus()
        
    def submit(self, event=None):
        row_index,col_index,meta_object = self.focus
        goto_next = True
        
        if self.mode == "META":
            if(meta_object == "row"):
                self.flat_tables[self.current_table_idx][row_index]["new_text"] = self.entry_contents.get()
                b = self.cells[row_index][0]
                b.configure(text=self.entry_contents.get())
            elif meta_object == "cell":
                self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]["new_text"] = self.entry_contents.get()
                b = self.cells[row_index][col_index]
                b.configure(text=self.entry_contents.get())
        elif meta_object == "element":
            elem_index = self.elem_index
            cell = self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]
            goto_next = True # dont go if changed
            
            if len(cell["data_items"]) > 0:
                qres = cell["data_items"][elem_index]

                if (self.measure.get() != qres["measure"]):
                    goto_next = False
                    qres["measure"] = self.measure.get()
                    
                self.property = StringVar()
                self.value = StringVar()
                self.att_label = StringVar()
                self.att_row = StringVar()
                self.att_col = StringVar()
                self.att_table = StringVar()
            
        if goto_next:
            self.next_focus()
        
    def prev(self): 
        row_index,col_index,meta_object = self.focus
        
        if(meta_object == "table"):
            if(len(self.data["tables"]) > 1):
                if(self.current_table_idx > 0):
                    self.current_table_idx -= 1
                else:
                    self.current_table_idx = len(self.data["tables"])-1
                self.update_window(self.current_table_idx)
            
            col_index = len(self.flat_tables[self.current_table_idx][0]["fields"])-1
            row_index = len(self.flat_tables[self.current_table_idx])-1
            meta_object = "cell"
            if self.mode == "GT":
                meta_object = "element"
                self.elem_index = len(self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]["data_items"])-1
                if (self.elem_index < 0): self.elem_index = 0
        elif(meta_object == "col"):
            if (col_index > 0):
                col_index = col_index - 1
            else:
                meta_object = "table"
        elif(meta_object == "row"):
            if (row_index > 0):
                row_index = row_index - 1
            else:
                col_index = len(self.flat_tables[self.current_table_idx][0]["fields"])-1
                meta_object = "col"
        elif(meta_object == "cell"):
            if (col_index > 0):
                col_index = col_index - 1
            elif (row_index > 0):
                row_index = row_index - 1
                col_index = len(self.flat_tables[self.current_table_idx][0]["fields"])-1
            else:
                meta_object = "row"
                row_index = len(self.flat_tables[self.current_table_idx])-1
        elif(meta_object == "element"):
            if(self.elem_index-1 < 0 ):
                # move to prev cell
                meta_object = "element"
                if (col_index > 0):
                    col_index = col_index - 1
                elif (row_index > 0):
                    row_index = row_index - 1
                    col_index = len(self.flat_tables[self.current_table_idx][0]["fields"])-1
                else:
                    meta_object = "table"
                if meta_object == "element":
                    cell = self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]
                    if (len(cell["data_items"]) > 0): self.elem_index = len(cell["data_items"])-1
                    else: self.elem_index = 0
            else:
                self.elem_index -= 1
        
        self.set_focus(row_index,col_index,meta_object)
        
    def next_focus(self):
        row_index,col_index,meta_object = self.focus
        
        if(meta_object == "table"):
            if self.mode == "META":
                col_index = 0
                meta_object = "col"
            else:
                row_index = 0
                col_index = 0
                self.elem_index = 0
                meta_object = "element"
        elif(meta_object == "col"):
            if (col_index+1 < len(self.flat_tables[self.current_table_idx][0]["fields"])):
                col_index = col_index + 1
            else:
                row_index = 0
                meta_object = "row"
        elif(meta_object == "row"):
            if (row_index+1 < len(self.flat_tables[self.current_table_idx])):
                row_index = row_index + 1
            else:
                row_index = 0
                col_index = 0
                meta_object = "cell"
        elif(meta_object == "cell"):
            if (col_index+1 < len(self.flat_tables[self.current_table_idx][0]["fields"])):
                col_index = col_index + 1
            elif (row_index+1 < len(self.flat_tables[self.current_table_idx])):
                row_index = row_index + 1
                col_index = 0
            else:
                meta_object = "table"
                if(self.current_table_idx+1 < len(self.data["tables"])):
                    self.current_table_idx += 1
                else:
                    self.current_table_idx = 0
                self.update_window(self.current_table_idx)
        elif(meta_object == "element"):
            cell = self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]
            if(self.elem_index+1 >= len(cell["data_items"]) ):
                # move to next cell
                self.elem_index = 0
                if (col_index+1 < len(self.flat_tables[self.current_table_idx][0]["fields"])):
                    col_index = col_index + 1
                elif (row_index+1 < len(self.flat_tables[self.current_table_idx])):
                    row_index = row_index + 1
                    col_index = 0
                else:
                    meta_object = "table"
                    if(self.current_table_idx+1 < len(self.data["tables"])):
                        self.current_table_idx += 1
                    else:
                        self.current_table_idx = 0
                    self.update_window(self.current_table_idx)
            else:
                self.elem_index += 1
            
        
        self.set_focus(row_index,col_index,meta_object)
        
    def set_focus(self, row_index, col_index, meta_object, elem_index = None):
        self.focus = (row_index,col_index,meta_object)
        if elem_index == None: elem_index = self.elem_index
        
        # reset all others
        if self.current_table_idx in self.skipped["table"]:
            self.tbllabel.configure(bg=skipped_color)
        else:
            self.tbllabel.configure(bg=normal_color)
            
        for i,b in enumerate(self.cols):
            color = normal_color
            if i in self.skipped["col"]:
                color = skipped_color
            b.configure(bg=color)
        for i,b in enumerate(self.rows):
            color = normal_color
            old_idx = self.get_old_row_idx(i, self.current_table_idx)
            if old_idx in self.skipped["row"]:
                color = skipped_color
            b.configure(bg=color)
        for i,brows in enumerate(self.cells):
            old_idx = self.get_old_row_idx(i, self.current_table_idx)
            for j,b in enumerate(brows):
                color = normal_color
                if old_idx in self.skipped["row"] or j in self.skipped["col"] or (old_idx,j) in self.skipped["cell"]:
                    color = skipped_color
                b.configure(bg=color)
        
        if (meta_object == "cell"):
            if(self.mode == "META"):
                self.cells[row_index][col_index].configure(bg="yellow")
                self.entry_contents.set(self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]["new_text"])
                self.entry_label.set("Cell ["+str(col_index)+","+str(row_index)+"]:")
            elif(self.mode == "GT" and len(self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]["data_items"]) > 0):
                meta_object = "element"
                elem_index = 0
        elif (meta_object == "row"):
            self.rows[row_index].configure(bg="yellow")
            for c in self.cells[row_index]:
                c.configure(bg="yellow")
            self.entry_contents.set(self.flat_tables[self.current_table_idx][row_index]["new_text"])
            self.entry_label.set("Row ["+str(row_index)+"]:")
        elif (meta_object == "col"):
            self.cols[col_index].configure(bg="yellow")
            for c in self.cells:
                c[col_index].configure(bg="yellow")
            self.entry_label.set("Col ["+str(col_index)+"]")
        elif (meta_object == "table"):
            self.tbllabel.configure(bg="yellow")
            self.entry_label.set("Table ["+str(self.current_table_idx)+"]")
        
        
        if (meta_object == "element"):
            self.cells[row_index][col_index].configure(bg="yellow")
            cell = self.flat_tables[self.current_table_idx][row_index]["fields"][col_index]
            self.entry_contents.set(cell["new_text"])
            display_idx = elem_index+1
            if len(cell["data_items"]) == 0: display_idx = 0
            self.entry_label.set("Cell ["+str(col_index)+","+str(row_index)+"], Element ("+str(display_idx)+"/"+str(len(cell["data_items"]))+"):")
            
            if elem_index < len(cell["data_items"]):
                qres = cell["data_items"][elem_index]

                self.measure.set(qres["measure"])
                self.property.set(qres["property"])
                self.value.set(qres["value"])
                self.att_label.set(qres["att_label"])
                self.att_row.set(qres["arow"])
                self.att_col.set(qres["acol"])
                self.att_table.set(qres["atable"])
            else: 
                self.measure.set("Measure")
                self.property.set("Property")
                self.value.set("Value")
                self.att_label.set("Attribute label")
                self.att_row.set("Att. row")
                self.att_col.set("Att. col")
                self.att_table.set("Att. table")

        
    
    def prepare_table(self,table, row_index):
        
        table["old_idx"] = row_index
        table["old_text"] = table["fields"][0]["text"]
        table["new_text"] = table["old_text"]
        
        # prepare cells
        for cell in table["fields"]:
            cell["new_text"] = cell["text"]
            cell["data_items"] = []
        
        # start as single row
        rows = [ table ]
        
        prev_rows = 1
        for record in table["records"]:
            rows += self.prepare_table(record, row_index+prev_rows )
            prev_rows += get_num_rows(record)
        
        return rows
    
    def get_old_row_idx(self, new_idx, table_idx):
        
        flat_table = self.flat_tables[table_idx]
        return flat_table[new_idx]["old_idx"]
        
        
    def save(self):
        
        if self.mode == "META":
            self.save_meta()
            
    def save_meta(self):
        
        tables = []
        
        for table_idx, table in enumerate(self.flat_tables):
        
            table_meta = {"new_idx":table_idx, "is_valid":True}
            if table_idx in self.skipped["table"]:
                table_meta["is_valid"] = False
        
            row_mappings = {}
            rows = {}

            for i,row in enumerate(table):
                if row["old_idx"] >= 0:
                    row_mappings[row["old_idx"]] = i
                row_object = {"new_idx":i,"old_idx":row["old_idx"],"old_text":row["old_text"],"new_text":row["new_text"], "is_valid":True}
                if row["old_idx"] in self.skipped["row"]:
                    row_object["is_valid"] = False
                rows[i] = row_object

                row_object["cells"] = {}
                for j,cell in enumerate(row["fields"]):
                    cell_object = {"old_text":cell["text"],"new_text":cell["new_text"],"row_idx":i,"col_idx":j,"is_valid":True}
                    if (i,j) in self.skipped["cell"]:
                        cell_object["is_valid"] = False
                    row_object["cells"][j] = cell_object

            cols = {}

            for j,cell in enumerate(table[0]["fields"]):
                    col_object = {"new_idx":j, "is_valid":True,"old_text":cell["text"],"new_text":cell["new_text"]}
                    if j in self.skipped["col"]:
                        col_object["is_valid"] = False
                    cols[j] = col_object
                    
            tables.append({"table_meta":table_meta,"row_mappings":row_mappings,"rows":rows,"cols":cols})
            
        root = {"tables":tables,"metameta":{"fn":self.meta_filename,"o_fn":self.filename,"datetime":str(datetime.datetime.now()),"v":"1.0.0"}}
        
        filename = self.meta_filename
        with open(filename, 'w', encoding='utf-8') as save_file:
              json.dump(root, save_file, indent=2)

        print("Saved meta file to "+filename+"\n")

        self.meta_object = root
        
        response = messagebox.askokcancel("Meta file saved", "The meta file has been saved to '"+filename+"'. Would you like to annotate a ground truth file?")
        
        if(response):
            self.change_mode_gt()
    
            

def get_num_rows(table):
    
    num_rows = 1
    
    for record in table["records"]:
        
        num_rows += get_num_rows(record)
        
    return num_rows
    
    
    
    
    
    
    
    
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, scrollbar_x_container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(scrollbar_x_container, orient="horizontal", command=canvas.xview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar_y.set)
        canvas.configure(xscrollcommand=scrollbar_x.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x = scrollbar_x

    