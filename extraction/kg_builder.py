#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The KG_Builder is the main class used to construct the KG from the tree table structure (Steps 3, 4)
"""

from enum import Enum
import rdflib
from rdflib.namespace import RDF
from xml.sax.saxutils import unescape
import copy
import nltk
from nltk.tokenize import MWETokenizer
from nltk.tokenize import WhitespaceTokenizer 
     
from .graph_framework import *
from .classifiers import *
from .study_subject_interpreter import *
        
class KG_Builder:
    """Build a KG by extracting data from tree tables.
    
    Attributes:
      TokenClassifiers (list): List of classifiers to use
      
    """
    
    # right now ordered as per left-to-right precendece
    # TODO, should be revamped to be made much more powerful + adaptable
    
    def __init__(self):
        """Initialize the KG builder with initial parameters.
        
        """
        self.TokenClassifiers = [Free_Value_Token_Classifier(), Concept_Token_Classifier(),NCBO_Token_Classifier()]
        
        #self.row_interpreter = ...doesnt interpret along rows anymore
        
    def build_KG(self, intermediate_structure):
        """Build the KG using the data provided
        
        The data should be in the form of a tree table extraction.
        Example: data = make_tree_tables(load_extraction(input_file))
        
        This function does not return anything, but modifies data such that
        it is in the form of a preliminary KG (using graph_framework classes)
        and can be serialized to a KG using cell["column"].translate(g) on
        each top-level cell in the structure.
        
        Parameters:
          intermediate_structure (dict) : The tree table extraction
        """
        
        # any preliminary stuff, e.g. footnote scanning, fixing broken multipage tables, w/e
    
        # iterate thru tables
        for t_num,table in enumerate(intermediate_structure["tables"]):
            
            #print(table["fields"][0].keys())
            
            # STEP 1
            # given a table, parse its cells
            
            self.parse_table(table)
            
            
            # divide into row header columns and non-row-header columns
            # TODO: add an actual heuristic. for now we just assume row[0] = headers

            # remember, a cell now keeps tracks of its parent and children. so all we need is the column header (field)
            rowhead_columns = [table["fields"][0]]
            data_columns = table["fields"][1:]

            # empty for now
            column_nodes = []
                         
            # STEP 2
            # parse all row header columns
            # (or rows, really. since we want to create 1 row interpreter per row, regardless of header columns)

            # TODO: Deal with this
            # self.parse_row(table, rowhead_columns)

            # STEP 3
            # now, parse all non-row-header columns

            # this is actually done columnally

            # 3.1 create column interpreter for each
            # 3.2 apply col_interpreter.interpret(cell) to each col header

            # remember, column interpreters themselves will be applying the row interpreters, recursively.
            for col in data_columns:
                column_nodes.append(self.parse_col(table, col))
            
            # STEP 4

            # Build the kg, via translate
                         
            # for each column_nodes... etc.
                         
            # Include some options for formal KG (e.g. conforms to SCO) or informal (includes references to the missing values)
            # remember to deal with translate in the node_wrapper at this point
        
    def parse_row(self, table, rowhead_columns):
        
        # 1. Create a row interpreter for this current row
        
        # 2. Apply the row interpreter to header columns (but maybe not literally? row_header.interpret, versus row_data.interpret)
        
        self.row_interpreter.interpret(rowhead_columns[0])
        
        # 3. Use parents to fill in additional data for this row interpreter
        #   (again, maybe not literally. Esp since they've already been interpreted)
        
        # 4. Assign this row interpreter to this table.
        
        # 4. Recurse on children.  

        for c in rowhead_columns[0]["col_children"]:
            self.parse_row(table, [c])
    
    def parse_col(self, table, col_header_cell):
        
        col_int = Study_Subject_Interpreter(self)
        col_int.interpret(col_header_cell)
        return col_int.base
                         
    # should rename to "parse table cells," as thats all this does
    def parse_table(self, table):
        
        for i, cell in enumerate(table["fields"]):
            self.parse_cell(table,i)
        for subtable in table["records"]:
            self.parse_table(subtable)
    
    def parse_cell(self, table, i):
        
        # given a cell (field) and its corresponding table, parse the cell
        
        cell = table["fields"][i]
        
        # first annotate with references to row parent, and column children
        # also annotate column children with references to column parent
        # if this cell is lacking a columnal parent, say so (via = none)
        
        # row parent:
        cell["row"] = table
        
        # index:
        cell["index"] = i
        
        # cell children:
        cell["col_children"] = []
        
        # set children to know this cell as columnal parent
        for subtable in table["records"]:
            
            child = subtable["fields"][i]
            child["col_parent"] = cell
            cell["col_children"].append(child)
        
        # does this cell have a parent?
        if "col_parent" not in cell:
            cell["col_parent"] = None
        
        
        # now, finally
        # do the initial extraction on this cell
        # this extraction is designed to identify and extract context-agnostic features
        # this includes value-type features, as well as interpreter-type features
        
        self.annotate_features(cell)
        
        # value-type features are node instances which are ready to be added to a graph... provided
        # the graph has the right method of interpreting these values
        
        # interpreter-type features are methods of interpreting values
        # when a cell with features is interpreted, these values (which may be node instances in their
        # own right) are combined with properties and compounded into a more complicated structure
        
        # this structure itself still needs additional information to be added to a graph
        # this is generally what columns do
        # a primary subject column will generally interpret and add its children in a specific way
        # secondary or child columns will also interpret/add children, but while they may use information
        # from their parent column, they are typically not directly added
        # this is why, when designing a primary subject column mechanism, one needs to account for the return
        # type of child cells, so as to know how to handle them.
        
        # in general, child cells return arrays of features to be added directly, OR they return a lack of array
        # this helps avoid type checking confusion
        # one should always practice constant vigilance, however
       
    
    def classify_token(self, token, cell):
        
        # given some token
        # return an array of features
    
        # given all these token classifiers. which have.
        # previously been gathered when this kg_builder was made.
        # use them. to. classify tokens.
        
        features = []
        
        for classifier in self.TokenClassifiers:
            features += classifier.classify(token, cell)
                
        return features;
                
        # POTENTIAL STICKING POINT
        # when multiple features match, all of the matching features are returned at once (in an array)
        # in this way, precendence issues are avoided
    
    def classify_pattern(self, cell):
        return []
        # given the initial feature identification in the cell
        
        # identify patterns based on PRESCENCE of tokens/features
        
        # ...TODO
        
        # identify patterns based on ABSCENCE of tokens/features
        # (e.g. a number was not matched to something.. erego it is a free value)
        
        # ...TODO
        
        # return a LIST of tuples, such that each element follows (LIST_OF_TOKENS, FEATURE)
        # so yes, some features may overlap in their corresponding tokens (again, avoids precedence issues)
    
    def annotate_features(self, cell):
        
        # first, tokenize
        
        #this one is better but doesnt handle some punct (e.g =) as well:
        #tokenizer = nltk.word_tokenize(cell["text"])
        
        # this one separates each punct as its own thing, EXCEPT for numbers (eg 40.3, -.6)
        # This one does not account for whitespace: r'-?\d*\.?\d+|\w+|[^\w\s]'
        # Current one accounts for 1 whitespace on either side of dot 
        tokenizer = nltk.tokenize.RegexpTokenizer(r'-?\s?\d*\s?\.\s?\d+|-?\s?\d*\.?\d+|\w+|[^\w\s]')
        
        #TODO: Refactor multi word tokens to work with keywords directly
        # Should be class-based (e.g. this array of keywords should be generated from the concept classifier, instead of included here)
        mwe = MWETokenizer([("s",".","d","."),("S",".","D","."),("standard","deviation"),("Standard","Deviation"),("Standard","deviation"),("s",".","e","."),("S",".","E","."),("standard","error"),("Standard","Error"),("Standard","error"),("st",".","dev","."),("St",".","Dev","."),("std",".","dev","."),("Std",".","Dev","."),("interquartile","range"),("Interquartile","Range"),("Interquartile","range"),("confidence","interval"),("Confidence","Interval"),("Confidence","interval"),("geometric","mean"),("Geometric","Mean"),("Geometric","mean"),("Coefficient","of","Variation")])

        #TODO: Glyphs, superscript/subscript
        # It might not be possible to account for glyphs, subscript might be solvable however
        
        # Examples:
        # GLYPH<C6> instead of ± (Only seen in one document)
        # GLYPH<shortrightarrow>
        # GLYPH<two.numr> (2 superscript I believe)
        # HbA$_{1c}$
        
        
        #TODO: Test that this works, make ways to account for other encodings 
        text = cell["text"] 
        if len(text) is not 0:
            # accounts for html wierdness
            text = unescape(text)
            # convert bullet (·) to decimal here
            text = text.replace('·','.')
            # convert minus sign (−) to - here
            text = text.replace('−','-')
            # TODO: Adjust such that minus sign is its own token/interpreter, that can create free values
            # Instead we just replace with '−' if range might be an issue
            lastnum = -10
            s = list(text)
            for i,c in enumerate(s):
                if c >= '0' and c <= '9':
                    lastnum = i
                if c == '-' and (i - lastnum) == 1: #if immediately following number
                    s[i] = '−'
            text = "".join(s)
                    
            
            tokens = tokenizer.tokenize(text)
        else: tokens = [] # otherwise it fills with "missing data"
        
        tokens = mwe.tokenize(tokens)
        
        # Examine each token according to the various token_extracters (token_classifiers? )
        # Store in cell
        
        cell["tokens"] = []
        
        for token in tokens:
            # strip whitespace
            token = token.replace(" ","")
            features = self.classify_token(token, cell)
            cell["tokens"].append((token, features))
        
        # next: redo but for patterns of tokens
        # proposal: use multi word tokenizing?
        
        cell["patterns"] = self.classify_pattern(cell)
            
        
        # now, this cell's own interpreters should start acting on the rest of the cell
        # possibly subsuming other features
        # and possibly turning from interpreters into value features
        # no idea how that will work
        
        
        # TODO: For step 1.3, just create a cell_interpreter, that calls interpret on this cell
        # thus building preliminary trees
        # or just wait it out, not that big a deal
        c_i = Cell_Interpreter(self)
        c_i.interpret(cell)
        
        
        
        