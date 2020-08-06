#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Contains several helper classes that are used to represent knowledge graph components before they are serialized to RDF.

Rather than just use RDFLib directly, these helper classes are used to facilitate the assembly of the knowledge graph
through additional metadata, pointers, and methods.

The basic structure of the classes is as follows:
  - Translatable refers to any object which can be serialized to RDF ('translated'). 
    - IRI_Node represents an IRI referenced within the KG
    - Literal_Node represents an RDF literal referenced within the KG
    - Node_Instance represents a Blank Node within the KG, and stores references to other Translatables
      - Individual_Instance represents an IRI declared within the KG, and stores references to other Translatables

Classes representing graph components follow the Composite design pattern. Translatables act as Components stored by
Node_Instances acting as Composites. In this way, a KG is assembled into a tree-like structure.
  
"""

from enum import Enum
import rdflib
from rdflib.namespace import RDF
import copy
import nltk
from nltk.tokenize import MWETokenizer
from nltk.tokenize import WhitespaceTokenizer 

#options that adjust the metadata that is included when nodes are serialized to RDF
include_longer_metadata = True
include_metadata = True
    
#################################################################################################################
# Base classes (informally abstract):
    
class Translatable:
    """A class to represent anything (generally graph nodes) that can be serialized to RDF.
    
    This class is informally abstract (not intended to be instantiated directly.)
    Instead, instantiate one of its subclasses.
    
    Translatables act as Components within the Composite design pattern.
    
    """
    
    def translate(self, kg):
        """Add this Translatable to the KG (if applicable) and return itself as an RDFLib object.
        
        Parameters:
          kg (rdflib.Graph): The knowledge graph that this Translatable is being added to.
        
        Returns:
          rdflib.term.Identifier: This object, translated to RDFLib
        """
        raise NotImplementedError(".translate() not implemented")
        
    def to_string(self):
        """Return a string representing this Translatable."""
        return "Undefined"
    
    def __repr__(self):
        return self.to_string()
    
    def __str__(self):
        return self.to_string();

class Feature:
    """Features are tablular elements which are extracted by any kind of classifier or extractor.
    
    This class is informally abstract (not intended to be instantiated directly.)
    Instead, instantiate one of its subclasses.
    
    Attributes:
      cell (dict): The cell this feature originates from.
      matching (list of strings): The list of tokens this feature matches.
      is_subsumed (bool): True if this Feature has been subsumed by another Feature, False otherwise.
      
    """
    # origin cell
    cell = None
    
    # matching pattern of [tokens]:
    # counter: these should be matched to a series of indices corresponding to tokens in cell
    # counter: can we have array of (index, token) tuples?
    matching = None
    
    # True if part of a bigger feature
    is_subsumed = False
    
    def get_type(self):
        """Get the type of this feature (one of blank, value, interpreter, or unknown).

        In general, features are value-type if they are complete and ready to be translated to RDF,
        and are interpreter-type if they inherit Interpreter and still need interpret() to be called.
        Sometimes, calling interpreter() on an interpreter-type will change it to a value-type.
        """
        raise NotImplementedError(".get_type() not implemented")
    
    def duplicate(self, cell):
        """Duplicate this feature to have a copy originating from cell. Return the copy.

        Specific features may duplicate according to specific ways. Use this method when a feature's
        information needs to be copied to a new feature corresponding to a different cell.

        Parameters:
          cell (dict): the home cell of the new duplicate feature.
          
        Returns:
          feature: the newly created duplicate of this feature
        """
        raise NotImplementedError(".duplicate(cell) not implemented")

class FeatureType(Enum):
    """Enumerated representation of feature type, as returned by Feature.get_type()"""
    BLANK = 0
    VALUE = 1
    INTERPRETER = 2
    UNKNOWN = 3    

class Interpreter():
    """Interpreters are mechanisms for combining features into trees within a certain cell
    
    This class is informally abstract (not intended to be instantiated directly.)
    Instead, instantiate one of its subclasses.
    
    They may try to fill all nodes with empties, or just try to create a specific type of node instance
    Different interpreters use different rules.
    
    Attributes:
      kg_builder (kg_builder): A pointer to the interpreter's kg_builder
    
    """
    
    def __init__(self, kg_builder):
        """Instantiate an Interpreter.

            Parameters:
              kg_builder (kg_builder): A pointer to the interpreter's kg_builder
        """
        self.kg_builder = kg_builder

    def interpret(self, cell):
        """Modify the cell by assembling its features into a composite or tree-like structure.

            Parameters:
              cell (dict): Cell to interpret.
        """
        raise NotImplementedError(".interpret() not implemented")
    
class SearchPattern(Enum):
    """Enumerated list of search patterns."""
    LEFT_TO_RIGHT = 0
    RIGHT_TO_LEFT = 1
    
#################################################################################################################
# Classes inheriting Translatable:
    
class IRI_Node(Translatable):
    """A class to represent IRIs referenced within the KG.
    
    This class is mainly a wrapper around an IRI string.
    
    This class is not intended to contain references to other Translatables. If instantiating
    a node instance in the KG with its own IRI, use Individual_Instance instead.
    
    Attributes:
      IRI_String (string): The IRI this node wraps around. May optionally not include the namespace IRI.
      ontology (string): The namespace IRI of this IRI_Node. None by default.

    """

    def __init__(self,IRI_String, ontology = None):
        """Instantiate an IRI_Node.
        
        Parameters:
          IRI_String (string): The IRI this node wraps around. May optionally not include the namespace IRI.
          ontology (string, optional): The namespace IRI of this IRI_Node. None by default.
        """
        self.IRI_String = IRI_String
        self.ontology = ontology
    
    def translate(self, kg):
        """Add this Translatable to the KG (if applicable) and return itself as an RDFLib object.
        
        Parameters:
          kg (rdflib.Graph): The knowledge graph that this Translatable is being added to.
        
        Returns:
          rdflib.term.Identifier: This object, translated to RDFLib
        """
        # QUICK FIX #1
        # Just manually identify what ontology this IRI_String is from by the prefix
        # In time, should change so that ontology is specified in the ontology variable (half) and prefixes should be entirely refactored into the RDFLib.Graph namespace manager
        
        #return rdflib.URIRef(self.IRI_String)
        
        if self.ontology is not None:
            return rdflib.URIRef(self.ontology+self.IRI_String)
        
        # Step 1: Identify prefix:
        tokens = self.IRI_String.split(":")
        prefix = tokens[0]
        infix = tokens[1]
        
        # Step 2: Determine correct ontology based on prefix
        ontology = prefix
        if prefix == "rdf":
            ontology = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        elif prefix == "rdfs":
            ontology = "http://www.w3.org/2000/01/rdf-schema#"
        elif prefix == "sio":
            ontology = "http://semanticscience.org/resource/"
        elif prefix == "sco":
            ontology = "https://idea.tw.rpi.edu/projects/heals/studycohort/"
        elif prefix == "owl":
            ontology = "http://www.w3.org/2002/07/owl#"
        #else:
            #print(prefix,self.IRI_String)
        
        full_iri = ontology+infix
        
        return rdflib.URIRef(full_iri)
    
    def to_string(self):
        """Return a string representing this Translatable."""
        return self.IRI_String
    
def cleanForIRI(string):
    """Cleans a string to be suitable for use as an IRI (punctation we dont want is removed)"""
    
    iri = ""
    
    for c in string:
        if c.isalnum() or c in ["-", ".", "_", "~"]:
            iri+=c
    return iri

class Literal_Node(Translatable):
    """A class to represent literal values referenced within the KG.
    
    This class is mainly a wrapper around a numerical or other RDF-compatible value, and is not intended
    to contain references to other Translatables.
    
    It should be noted that Literal_Node is intended to be used as a base class for other classes, such
    as Free_Value. Unlike Free_Value, Literal_Node does not contain any metadata about the tabular
    origin of the value--only use Literal_Node directly if this is desired.
    
    Attributes:
      value: The value this node represents. Can be of any data type supported by RDFLib literals.
    
    """

    def __init__(self, value = None):
        """Instantiate a Literal_Node
        
        Parameters:
          value (optional): Can be of any data type supported by RDFLib literals. None by default.
        """
        self.value = None
    
    def translate(self, kg):
        """Add this Translatable to the KG (if applicable) and return itself as an RDFLib object.
        
        Parameters:
          kg (rdflib.Graph): The knowledge graph that this Translatable is being added to.
        
        Returns:
          rdflib.term.Identifier: This object, translated to RDFLib
        """
        return rdflib.Literal(self.value)
    
    def to_string(self):
        """Return a string representing this Translatable."""
        if self.value is None:
            return "< # >"
        if isinstance(self.value, str): return "\""+self.value+"\""
        return str(self.value)

#################################################################################################################
# Classes inheriting Feature (and optionally Translatable):
    
class Free_Value(Feature, Literal_Node):
    """A class to represent values found within a table cell.
    
    It should be noted that unlike Literal_Node, Free_Value is a feature and therefore contains
    additional metadata relating to the tabular nature of the original free value.
    
    Attributes:
      value: The value this node represents. Can be of any data type supported by RDFLib literals.
      cell (dict): The cell this feature originates from.
      matching (list of strings): The list of tokens this feature matches.
      is_subsumed (bool): True if this Feature has been subsumed by another Feature, False otherwise.
      
    """
    # anything which is a literal (e.g a number. could also be a string)
    
    # setup initial values for this object
    # what are these initial values?
    # well, we need to know what the VALUE this literal represents IS.
    # everything else-- that is, cell, matching, etc. -- that can be done by the user
    # although matching at least should probably be supplied at runtime
    #   counter-- what if it can't? maybe just remember to set it
    #     counter-- if it can't, provide 'none.' Less things you need to remember to set, the better.
    
    def __init__(self, matching, cell, value): 
        """Instantiate a Literal_Node
        
        Parameters:
          cell (dict): The cell this feature originates from.
          matching (list of strings): The list of tokens this feature matches.
          value : Can be of any data type supported by RDFLib literals. None by default.
        """
        self.value = value
        self.matching = matching
        self.cell = cell
        self.is_subsumed = False
        
    def get_type(self):
        """Get the type of this feature (one of blank, value, interpreter, or unknown).

        In general, features are value-type if they are complete and ready to be translated to RDF,
        and are interpreter-type if they inherit Interpreter and still need interpret() to be called.
        Sometimes, calling interpreter() on an interpreter-type will change it to a value-type.
        """
        return FeatureType.VALUE
    
    def duplicate(self, cell):
        """Duplicate this feature to have a copy originating from cell. Return the copy.

        Free_Value creates a new Free_Value object, but with references to the same value
        and matching attributes. Behavior may be changed to deepcopy.

        Parameters:
          cell (dict): the home cell of the new duplicate feature.
          
        Returns:
          feature: the newly created duplicate of this feature
        """
        return Free_Value(self.matching,cell,self.value)
    
class Node_Instance (Feature, Translatable):
    """Corresponds to some kind of node instance (blank node, typically instantiating a class)
    
    Contains a tuple of complete triples (predicate and object are determined) and
    incomplete triples (predicate is determined, object is not determined but is constrained).
    
    The missing object within incomplete triples should be "filled" with an appropriate object
    before this node is translated. Any incomplete triples which are not filled will be ignored
    during translation.
    
    Attributes:
      cell (dict): The cell this feature originates from.
      matching (list of strings): The list of tokens this feature matches.
      is_subsumed (bool): True if this Feature has been subsumed by another Feature, False otherwise.
      triples: a list of (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof TRANSLATABLE). Together
        with this node_instance as the subject, they form a list of triples attached to this node.
      incomplete triples: a list of (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof CONSTRAINT)
                                 or (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof TRANSLATABLE)
        where OBJECT_NODE is replaced with the correct blank node or literal node when filled.
        If OBJECT_NODE is of typeof TRANSLATABLE, it can be filled by any node of the same type.
      bnode (RDFLib.Term.Bnode): The most recently created RDFLib BNode. Initially None.
    """
    #todo: instead of using translatables as constraints, make new Constraint classes. 
    
    # init: give array of matching tokens, as well as initial cell
    def __init__(self, matching, cell): 
        """Instantiate a Node_Instance.
        
        Parameters:
          matching (list of strings): The list of tokens this feature matches.
          cell (dict): The cell this feature originates from.
        """
        self.cell = cell
        self.matching = matching
        self.triples = []
        self.incomplete_triples = []
        self.bnode = None
    
    def translate(self, kg):
        """Add this Translatable to the KG (if applicable) and return itself as an RDFLib object.
        
        The 'bnode' attribute is set as a result of calling this method.
        
        Parameters:
          kg (rdflib.Graph): The knowledge graph that this Translatable is being added to.
        
        Returns:
          rdflib.term.Identifier: This object, translated to RDFLib
        """
        self.bnode = rdflib.BNode()
        
        for triple in self.triples:
            kg.add( (self.bnode, triple[0].translate(kg), triple[1].translate(kg) ) )
            
        # TODO: Add something for dealing with translating incomplete triples
        
        # Cell/row/table provenance for sequencing
        if include_metadata and self.cell is not None:
            if include_longer_metadata:
                kg.add( (self.bnode, IRI_Node("sco:rowIndex",None).translate(kg), rdflib.Literal(self.cell["spans"][0][0]) ) )
                kg.add( (self.bnode, IRI_Node("sco:colIndex",None).translate(kg), rdflib.Literal(self.cell["spans"][0][1]) ) )
                kg.add( (self.bnode, IRI_Node("sco:tableIndex",None).translate(kg), rdflib.Literal(self.cell["table_num"]) ) )
            else:
                spans = str(self.cell["spans"][0][0])+","+str(self.cell["spans"][0][1])+","+str(self.cell["table_num"])
                kg.add( (self.bnode, IRI_Node("sco:cellSpans",None).translate(kg), rdflib.Literal(spans) ) )
        
        
        return self.bnode
    
    # fill: fill incomplete_triples[index] with object_candidate, then remove from incomplete and add to the triples
    # object_node is typeof translatable
    # return if success or failure
    def try_fill(self, object_candidate, index):
        """Attempt to fill the incomplete triple at position 'index' with 'object_candidate'.

        If succesful, the incomplete triple is removed from incomplete_triples and add to the triples
        attribute, with its new object.
        This method is unsuccesful when object_candidate does not satisfy the constraint of the
        incomplete triple that was attempted.

        Parameters:
          object_candidate (Translatable): The object to attempt to fill the incomplete triple with.
          index (int): The position of the incomplete triple to fill within incomplete_triples.

        Returns:
          bool : True if the incomplete triple was sucessfully filled, False otherwise.
        """
        triple = self.incomplete_triples[index]
        constraint = triple[1]
        
        # test the object
        if self.satisfies(object_candidate, constraint):
            # if it can be added, add it
            new_triple = (triple[0], object_candidate)
            self.incomplete_triples.pop(index)
            self.triples.append(new_triple)
            
            # adjust matching if neccesary
            if isinstance(object_candidate, Feature):
                self.matching += object_candidate.matching
            
            # mark the object
            object_candidate.is_subsumed = True
            
            return True
        
        else: return False

    # like try_fill, but does not modify anything. just returns if success or failure
    def can_fill(self, object_candidate, index):
        """Test whether 'object_candidate' can fill the incomplete triple at position 'index'.

        The object candidate can fill the incomplete triple when object_candidate satisfies the
        object constraint of the incomplete triple that was attempted.

        Parameters:
          object_candidate (Translatable): The object to attempt to fill the incomplete triple with.
          index (int): The position of the incomplete triple to fill within incomplete_triples.

        Returns:
          bool : True if the incomplete triple can be filled, False otherwise.
        """
        triple = self.incomplete_triples[index]
        constraint = triple[1]
        
        # test the object
        if self.satisfies(object_candidate, constraint):
            # if it can be added, don't add it
            
            return True
        
        else: return False
        
    # determine if object_candidate meets object_constraint
    # TODO: Add heuristics and interpreters
    def satisfies(self, object_candidate, object_constraint):
        """Test whether 'object_candidate' meets 'object_constraint.'

        If true, object_candidate can be used to fill an incomplete triple with
        object_constraint.

        Returns:
          bool : True if the object_constraint is met by object_candidate, False otherwise.
        """
        # is the object_candidate a Literal_Node?
        if isinstance(object_candidate, Literal_Node):
            if isinstance(object_constraint, Literal_Node):
                return True
                
        # is the object_candidate an IRI?
        elif isinstance(object_candidate, IRI_Node):
            if isinstance(object_constraint, IRI_Node):
                return True
            
        # is the object_candidate a Node_Instance?
        elif isinstance(object_candidate, Node_Instance):
            if isinstance(object_constraint, Supertype_Constraint):
                return object_constraint.is_supertype_of(object_candidate)
            if isinstance(object_constraint, Node_Instance):
                # TODO: Actually write this part (compare IRIs?)
                # TODO: Implement SPARQL
                return False
        
        return False
                
    # return a duplicate of this node instance
    # triples, incomplete_triples are copied
    # cell is provided new, however
    def duplicate(self, cell):
        """Duplicate this feature to have a copy originating from cell. Return the copy.

        Node_Instance creates a new Node_Instance object, with copies of the triples and
        incomplete_triples lists. The lists reference the same objects, however (no use
        of deepcopy).

        Parameters:
          cell (dict): the home cell of the new duplicate feature.

        Returns:
          feature: the newly created duplicate of this feature
        """
        n = Node_Instance(self.matching, cell)
        
        # note that IRI nodes and objects are not duplicated
        # they don't need to be -- they shouldn't be modified
        # objects in complete triples are just that-- complete
        # objects in incomplete triples are replaced when completed
        
        n.triples = self.triples[:]
        n.incomplete_triples = self.incomplete_triples[:]
        
        return n
        
    def get_type(self):
        """Get the type of this feature (one of blank, value, interpreter, or unknown).

        In general, features are value-type if they are complete and ready to be translated to RDF,
        and are interpreter-type if they inherit Interpreter and still need interpret() to be called.
        Sometimes, calling interpreter() on an interpreter-type will change it to a value-type.
        """
        return FeatureType.VALUE
        # pretty sure its never interpreter type
        # TODO: think about that
        
    def to_string(self):
        """Return a string representing this Translatable."""
        if len(self.incomplete_triples) > 0 and False:
            string = "<"
        else: string = "["
        for t in self.triples:
            string+= t[0].to_string()+" "+t[1].to_string()+"; "
        for t in self.incomplete_triples:
            string+= t[0].to_string()+" "+t[1].to_string()+"; "
        if len(self.incomplete_triples) > 0 and False:
            string += ">"
        else: string += "]"
        return string

# Represents an instance (e.g. something with sco-i in the prefix)
# Essentially identical to a node_instance, but has an IRI and an ontology
class Individual_Instance(Node_Instance):
    """Corresponds to a new individual (with its own IRI) instantiated within the KG.
    
    Contains a tuple of complete triples (predicate and object are determined) and
    incomplete triples (predicate is determined, object is not determined but is constrained).
    
    The missing object within incomplete triples should be "filled" with an appropriate object
    before this node is translated. Any incomplete triples which are not filled will be ignored
    during translation.
    
    Attributes:
      cell (dict): The cell this feature originates from.
      matching (list of strings): The list of tokens this feature matches.
      IRI_String (string): The IRI this node wraps around. May optionally not include the namespace IRI.
      ontology (string, optional): The namespace IRI of this IRI_Node. None by default.
      is_subsumed (bool): True if this Feature has been subsumed by another Feature, False otherwise.
      triples: a list of (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof TRANSLATABLE). Together
        with this node_instance as the subject, they form a list of triples attached to this node.
      incomplete triples: a list of (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof CONSTRAINT)
                                 or (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof TRANSLATABLE)
        where OBJECT_NODE is replaced with the correct blank node or literal node when filled.
        If OBJECT_NODE is of typeof TRANSLATABLE, it can be filled by any node of the same type.
      bnode (RDFLib.Term.URIRef): The most recently created RDFLib URIRef (not BNode). Initially None.
      
    """
    
    # init: give array of matching tokens, as well as initial cell
    #  since this is an individual, give it an IRI_String and an ontology as well
    def __init__(self, matching, cell, IRI_String, ontology): 
        """Instantiate an Individual_Instance.
        
        Parameters:
          matching (list of strings): The list of tokens this feature matches.
          cell (dict): The cell this feature originates from.
          IRI_String (string): The IRI this node wraps around. May optionally not include the namespace IRI.
          ontology (string, optional): The namespace IRI of this IRI_Node. None by default.
        """
        self.cell = cell
        self.matching = matching
        self.triples = []
        self.incomplete_triples = []
        self.bnode = None
        
        self.IRI_String = IRI_String
        if ontology is not None:
            self.ontology = ontology
        else:
            self.ontology = ""
        
    def translate(self, kg):
        """Add this Translatable to the KG (if applicable) and return itself as an RDFLib object.
        
        The 'bnode' attribute is set as a result of calling this method.
        
        Parameters:
          kg (rdflib.Graph): The knowledge graph that this Translatable is being added to.
        
        Returns:
          rdflib.term.Identifier: This object, translated to RDFLib
        """
        # Essentially the same, only difference it is not a bnode, it is an individual with its own IRI
        self.bnode = rdflib.URIRef(self.ontology+self.IRI_String)
        
        for triple in self.triples:
            kg.add( (self.bnode, triple[0].translate(kg), triple[1].translate(kg) ) )
            
        # TODO: Add something for dealing with translating incomplete triples
        
        # Cell/row/table provenance for sequencing
        if include_metadata and self.cell is not None:
            if include_longer_metadata:
                kg.add( (self.bnode, IRI_Node("sco:rowIndex",None).translate(kg), rdflib.Literal(self.cell["spans"][0][0]) ) )
                kg.add( (self.bnode, IRI_Node("sco:colIndex",None).translate(kg), rdflib.Literal(self.cell["spans"][0][1]) ) )
                kg.add( (self.bnode, IRI_Node("sco:tableIndex",None).translate(kg), rdflib.Literal(self.cell["table_num"]) ) )
            else:
                spans = str(self.cell["spans"][0][0])+","+str(self.cell["spans"][0][1])+","+str(self.cell["table_num"])
                kg.add( (self.bnode, IRI_Node("sco:cellSpans",None).translate(kg), rdflib.Literal(spans) ) )
        
        return self.bnode
    
    def to_string(self):
        """Return a string representing this Translatable."""
        return "sco-i:"+self.IRI_String
    
class Concept_Feature(IRI_Node,Feature):
    """A class to represent IRIs of concepts found within the KG.
    
    This class is mainly a wrapper around an IRI string.
    
    This class is not intended to contain references to other Translatables. If instantiating
    a node instance in the KG with its own IRI, use Individual_Instance instead.
    
    Attributes:
      cell (dict): The cell this feature originates from.
      matching (list of strings): The list of tokens this feature matches.
      is_subsumed (bool): True if this Feature has been subsumed by another Feature, False otherwise.
      IRI_String (string): The IRI this node wraps around. May optionally not include the namespace IRI.
      ontology (string): The namespace IRI of this IRI_Node. None by default.
      IRI_Parents (list): List of IRI nodes this node is a subtype of. Empty by default.
      
    """

    def __init__(self, cell, matching, IRI_String, ontology = None, IRI_Parents = []):
        """Instantiate a Concept_Feature.
        
        Parameters:
          cell (dict): The cell this feature originates from.
          matching (list of strings): The list of tokens this feature matches.
          IRI_String (string): The IRI this node wraps around. May optionally not include the namespace IRI.
          ontology (string, optional): The namespace IRI of this IRI_Node. None by default.
          IRI_Parents (list, optional): List of IRI nodes this node is a subtype of. Empty by default.
        """
        self.cell = cell
        self.matching = matching
        self.is_subsumed = False
        
        self.IRI_String = IRI_String
        self.ontology = ontology
        self.IRI_Parents = IRI_Parents
    
    def get_type(self):
        """Get the type of this feature (one of blank, value, interpreter, or unknown).

        In general, features are value-type if they are complete and ready to be translated to RDF,
        and are interpreter-type if they inherit Interpreter and still need interpret() to be called.
        Sometimes, calling interpreter() on an interpreter-type will change it to a value-type.
        """
        return FeatureType.VALUE
    
    def duplicate(self, cell):
        """Duplicate this feature to have a copy originating from cell. Return the copy.

        Specific features may duplicate according to specific ways. Use this method when a feature's
        information needs to be copied to a new feature corresponding to a different cell.

        Parameters:
          cell (dict): the home cell of the new duplicate feature.
          
        Returns:
          feature: the newly created duplicate of this feature
        """
        c = Concept_Feature(cell, self.matching, self.IRI_String, self.ontology, self.IRI_Parents)
        return c
    
#################################################################################################################
# Classes inheriting Interpreter (and optionally Feature and/or Translatable):
# More complex Interpreters are given their own file. Basic Interpreters are included here.

# just build trees within this cell
# calls any interpreter-types within this cell
class Cell_Interpreter(Interpreter):
    """A basic Interpreter which recursively calls Interpreter-type Features within a cell.
    
    This class represents a Composite design type, operating on the component Features within a cell. 
    
    Attributes:
      kg_builder (kg_builder): A pointer to the interpreter's kg_builder
      
    """
    
    def interpret(self, cell):
        """Modify the cell by assembling its features into a composite or tree-like structure.

           Parameters:
              cell (dict): Cell to interpret.
        """
        for (tok, features) in cell["tokens"]:
            for f in features:
                if f.get_type() is FeatureType.INTERPRETER:
                    f.interpret(cell)
                    
# A class which is a node instance with an accompanying interpret() method.
# This interpret method just scans, left-to-right or right-to-left, from each matching token
# until the value is filled or the end of the tokens is reached.
# When it fills all of its missing triples, it becomes value-type.
class Simple_Node_Interpreter(Node_Instance, Interpreter):
    """A Node_Instance which can fill its own incomplete triples by searching a cell in a specific direction.
    
    Attributes:
      cell (dict): The cell this feature originates from.
      matching (list of strings): The list of tokens this feature matches.
      is_subsumed (bool): True if this Feature has been subsumed by another Feature, False otherwise.
      triples: a list of (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof TRANSLATABLE). Together
        with this node_instance as the subject, they form a list of triples attached to this node.
      incomplete triples: a list of (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof CONSTRAINT)
                                 or (PREDICATE -- typeof IRI_NODE, OBJECT_NODE -- typeof TRANSLATABLE)
        where OBJECT_NODE is replaced with the correct blank node or literal node when filled.
        If OBJECT_NODE is of typeof TRANSLATABLE, it can be filled by any node of the same type.
      bnode (RDFLib.Term.Bnode): The most recently created RDFLib BNode. Initially None.
      search_pattern (SearchPattern): The direction to search.
      
    """
    #TODO: Missing kg_builder attribute. Is this worthwhile to fix?
    # not including type in the attributes above as get_type should be used instead 
    #  (TODO: change type to private, e.g. _type)
    
    # init: give array of matching tokens, as well as initial cell, and initial direction to search
    def __init__(self, matching, cell, search_pattern): 
        """Instantiate a Simple_Node_Interpreter.

           Parameters:
              matching (list of strings): The list of tokens this feature matches.
              cell (dict): The cell this feature originates from.
              search_pattern (SearchPattern): The direction to search.
        """
        self.cell = cell
        self.matching = matching
        self.triples = []
        self.incomplete_triples = []
        self.search_pattern = search_pattern
        
        self.is_subsumed = False
        self.bnode = None
        self.type = FeatureType.INTERPRETER
        
    # Just interpret (build ASTs in) this cell
    def interpret(self, cell):
        """Modify the cell by assembling its features into a composite or tree-like structure.

           Parameters:
              cell (dict): Cell to interpret.
        """
        # TODO: Deal with S-expressions, continuing/stopping based on certain tokens found, etc.
        # For now, just move from each token in matching until either. A. a matching value is found or B. another INTERPRETER-type is found
        
        # move from token this node is attached to, onward
        is_scanning = False

        # search in correct direction
        cell_tokens = self.cell["tokens"]
        if self.search_pattern is SearchPattern.RIGHT_TO_LEFT:
            cell_tokens = cell_tokens[::-1]

        # check each token's features-
        #  first for this node,
        #  then for anything that will fill this node 
        for (tok, features) in cell_tokens:
            for f in features:
                if f is self:
                    is_scanning = True
                    continue
                if is_scanning and not f.is_subsumed:
                    # try to fill each triple
                    for i,t in enumerate(self.incomplete_triples):
                        if self.try_fill(f, i):
                            # here, tok that has f is marked with f
                            features.append(f)
                            break
        if len(self.incomplete_triples) == 0:
            self.type = FeatureType.VALUE
       
    def get_type(self):
        """Get the type of this feature (one of blank, value, interpreter, or unknown).

        In general, features are value-type if they are complete and ready to be translated to RDF,
        and are interpreter-type if they inherit Interpreter and still need interpret() to be called.
        Sometimes, calling interpreter() on an interpreter-type will change it to a value-type.
        """
        return self.type
        # interpreter-type if unfilled, value if filled 
        
#################################################################################################################
# Constraints
#TODO: At present, there is only the one constraint. In the future an abstract base Constraint class should be created,
# along with additional Constraint types.
        
# A class that is to be used as a constraint by try_fill
# Long story short, it returns true when a candidate is of a type that is either this type or a subtype of this type
class Supertype_Constraint:
    """Represents a constraint that can only be satisfied by objects that this constraint is a supertype of.
    
    An object is considered to be its own supertype.
    
    Attributes:
      supertype_IRI (string): The supertype this object represents
      can_be_node_instance (bool): Initially False. Set to True if an Individual_Instance can satisfy this constraint,
        but a Node_Instance cannot.
        
    """
    
    def __init__(self, supertype_IRI): 
        """Instantiate a Supertype_Constraint.

           Parameters:
              supertype_IRI (string): The supertype this object represents
        """
        self.supertype_IRI = supertype_IRI
        #TODO: This should really be its own, separate constraint.
        self.can_be_node_instance = True
        
    # candidate is node instance
    # return true if match, false otherwise
    def is_supertype_of(self, candidate):
        """Return True if this Supertype_Constraint is a supertype of candidate.
        
        Parameters:
          Candidate (Translatable): The candidate to test the type relationship of.
          
        Returns:
          bool : True if this Supertype_Constraint is a supertype of candidate, False otherwise.
        """
        subtype = None
        
        if self.supertype_IRI == "sco:SubjectCharacteristic":
            print("subjcar")
        
        if isinstance( candidate, Node_Instance):
            if not self.can_be_node_instance:
                return False
            for t in candidate.triples:
                # TODO: When rewriting code to use ontologies to determine inheritance associations between concept, adjust here
                if "type" not in t[0].IRI_String.lower():
                    continue
                subtype = t[1]
                break
                
            if subtype is None:
                for t in candidate.incomplete_triples:
                    if "type" not in t[0].IRI_String.lower():
                        continue
                    subtype = t[1]
                    
        """
        if isinstance( candidate, Concept_Feature):
            return True
            print("concfeat "+candidate.IRI_String)
            print("iri "+self.supertype_IRI.IRI_String)
            if self.supertype_IRI.IRI_String == candidate.IRI_String :
                return True
            for iri_parent in candidate.IRI_Parents:
                print("piri "+iri_parent.IRI_String)
                if self.supertype_IRI.IRI_String == iri_parent.IRI_String :
                    return True
            return False
        """
                    
        if subtype is None:
            return False
        
        # TODO: Identify parent-subclass relationships by loading in an ontology, rather than the manual checking I have right now
        
        if isinstance(subtype, Supertype_Constraint):
            subtype = subtype.supertype_IRI
            
        if isinstance(subtype, IRI_Node):
            if subtype.IRI_String == self.supertype_IRI.IRI_String:
                return True
            
            # just for testing:
            if self.supertype_IRI.IRI_String == "sco:CentralTendencyMeasure":
                if subtype.IRI_String == "sio:Mean" or subtype.IRI_String == "sco:GeometricMean" or subtype.IRI_String == "sio:Median":# or subtype.IRI_String == "sco:PopulationSize":
                    return True
            if self.supertype_IRI.IRI_String == "sco:DispersionMeasure":
                if subtype.IRI_String == "sio:StandardDeviation" or subtype.IRI_String == "sco:StandardError" or subtype.IRI_String == "sco:InterquartileRange" or subtype.IRI_String == "sco:ConfidenceInterval" or subtype.IRI_String == "sco:Range" or subtype.IRI_String == "sco:CoefficientOfVariation":# or subtype.IRI_String == "sio:Percentage":
                    return True
            if self.supertype_IRI.IRI_String == "sco:StatisticalMeasure":
                if subtype.IRI_String == "sio:Mean" or subtype.IRI_String == "sio:Median" or subtype.IRI_String == "sio:StandardDeviation" or subtype.IRI_String == "sco:StandardError" or subtype.IRI_String == "sco:InterquartileRange"or subtype.IRI_String == "sco:ConfidenceInterval" or subtype.IRI_String == "sco:Range" or subtype.IRI_String == "sco:GeometricMean" or subtype.IRI_String == "sco:CoefficientOfVariation" or subtype.IRI_String == "sio:Percentage" or subtype.IRI_String == "sco:PopulationSize":
                    return True
                
            
        return False
    
    def to_string(self):
        """Return a pseudo-rdf string representation of this Supertype_Constraint."""
        return "< rdfs:subtype+ "+self.supertype_IRI.to_string()+">"
    
    def __str__(self):
        return self.to_string()
    
    def __repr__(self):
        return self.to_string()