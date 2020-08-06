#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Contains the classifiers used in Step 3 of the pipeline to assign features to tokens.

   2 base, informally abstract classes:
     Token_Classifier: classifies tokens
     Pattern_Classifier: classifies groups of tokens
   3 Additional classes:
     Free_Value_Token_Classifier
     Concept_Token_Classifier
     NCBO_Token_Classifier
"""
import nltk
from nltk.tokenize import MWETokenizer
from nltk.tokenize import WhitespaceTokenizer 
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet

from .graph_framework import *
from . import annotate_text

class Token_Classifier:
    """Contains rules for how to classify (assign feature(s) to) a single token (if at all).
    
    This class is informally abstract (not intended to be instantiated directly.)
    Instead, instantiate one of its subclasses.
    
    """
    
    # a class that. you guessed it. classifies tokens.
    #specifically, given <token> in <cell>, classify returns [<feature1>, <feature2>, ...]
    # or empty array if no features identified via this classifier
    
    def classify(self, token, cell):
        """Given a token from a cell, return a corresponding list of features.
        
        Parameters:
          token (string): The token to classify
          cell (dict): The cell this token is found in
          
        Returns:
          list : List of features. May have multiple features, or none at all.
        """
        raise NotImplementedError(".classify(token, cell) not implemented")
        
class Pattern_Classifier:
    """Contains rules for how to classify (assign feature(s) to) groups of tokens (if at all).
    
    This class is informally abstract (not intended to be instantiated directly.)
    Instead, instantiate one of its subclasses.
    
    """
    
    #given <cell> already annotated with tokens, returns [<feature1>, <feature2>, ...]
    # or empty array if no features found
    
    def classify(self, token, cell):
        """Given a token from a cell, return a corresponding list of features.
        
        Parameters:
          token (string): The token to classify
          cell (dict): The cell this token is found in
          
        Returns:
          list : List of features. May have multiple features, or none at all.
        """
        raise NotImplementedError(".classify(token, cell) not implemented")
    
# specifically intended as a testing class
# most classifiers should not have a rigid, pre-coded classifier specifically for them.
class Free_Value_Token_Classifier (Token_Classifier):
    """The free value token classifier parses numerical values to assign features."""
    
    def classify(self, token, cell):
        """Given a token from a cell, return a corresponding list of features.
        
        Parameters:
          token (string): The token to classify
          cell (dict): The cell this token is found in
          
        Returns:
          list : List of features. May have multiple features, or none at all.
        """
        try:
            value = float(token)
            return [Free_Value([token], cell, value)] # TODO: Change how matching works
        except ValueError:
            return []
        
# specifically intended as a testing class
# most concepts should not have a rigid, pre-coded classifier specifically for them.
class Concept_Token_Classifier (Token_Classifier):
    """The concept token classifier performs keyword matching to classify tokens as features.
    
    At present, the concept token classifier uses hard-coded keywords. This should be changed
    to have it read in keywords from a config file.
    
    """
    
    # classifier returns ARRAY of features matching this token
    # TODO: Change how matching works
    def classify(self, token, cell):
        """Given a token from a cell, return a corresponding list of features.
        
        Parameters:
          token (string): The token to classify
          cell (dict): The cell this token is found in
          
        Returns:
          list : List of features. May have multiple features, or none at all.
        """
        if token.upper() == "Mean".upper() or token.upper() == "Average".upper():
            return [self.make_blank_node([token], cell, IRI_Node("sio:Mean",None))]
        if token.upper() == "GM".upper() or token.upper() == "geometric_mean".upper():
            return [self.make_blank_node([token], cell, IRI_Node("sco:GeometricMean",None))]
        elif token.upper() == "Median".upper():
            return [self.make_blank_node([token], cell, IRI_Node("sio:Median",None))]
        elif token.upper() == "SD".upper() or token.upper() == 's_._d_.'.upper() or token.upper() == 'standard_deviation'.upper() or token.upper() == 'Std_._Dev_.'.upper() or token.upper() == 'St_._Dev_.'.upper():
            return [self.make_blank_node([token], cell, IRI_Node("sio:StandardDeviation",None))]
        elif token.upper() == "SE".upper() or token.upper() == 's_._e_.'.upper() or token.upper() == 'standard_error'.upper():
            return [self.make_blank_node([token], cell, IRI_Node("sco:StandardError",None))]
        elif token.upper() == "%".upper() or token.upper() == "Percent".upper():
            #return [self.make_blank_node([token], cell, IRI_Node("sio:Percentage",None))]
            n = self.make_simple_node_interpreter([token], cell, IRI_Node("sio:Percentage",None), SearchPattern.RIGHT_TO_LEFT)
            n.incomplete_triples.append( (IRI_Node("sio:inRelationTo", None), Supertype_Constraint(IRI_Node("owl:Class",None))) )
            return [n]
        elif token.upper() == "IQR".upper() or token.upper() == 'interquartile_range'.upper():
            return [self.make_double_blank_node([token], cell, IRI_Node("sco:InterquartileRange",None))]
        elif token.upper() == "CI".upper() or token.upper() == 'confidence_interval'.upper():
            return [self.make_double_blank_node([token], cell, IRI_Node("sco:ConfidenceInterval",None))]
        elif token.upper() == "CV".upper() or token.upper() == 'coefficient_of_variation'.upper():
            return [self.make_double_blank_node([token], cell, IRI_Node("sco:CoefficientOfVariation",None))]
        elif token.upper() == "Range".upper():
            return [self.make_double_blank_node([token], cell, IRI_Node("sco:Range",None))]
        elif token.upper() == "N".upper() or token.upper() == "No".upper():
            #return [self.make_blank_node([token], cell, IRI_Node("sco:PopulationSize",None))]
            return [self.make_simple_node_interpreter([token], cell, IRI_Node("sco:PopulationSize",None), SearchPattern.LEFT_TO_RIGHT)]
        else: return []
        
    # just return the correct blank node
    def make_blank_node(self, matching, cell, parent_iri):
        """Helper function to make a blank node living in 'cell', matching tokens 'matching', of type 'parent_iri'"""
        
        n = Node_Instance(matching, cell)
        
        # add known triples (instanceof IRI)
        n.triples.append( (IRI_Node("rdf:type", None), parent_iri) )
        
        # add constraints
        # assuming these are all continuous characteristics. which shouldn't be assumed
        n.incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
        
        return n
    
    # For ranges, TODO: Refactor with other method
    def make_double_blank_node(self, matching, cell, parent_iri):
        """Helper function to make a double blank node living in 'cell', matching tokens 'matching', of type 'parent_iri'
        
        Double blank nodes are simply blank nodes with a minValue and maxValue, as opposed to only one value.
        """
        
        n = Node_Instance(matching, cell)
        
        # add known triples (instanceof IRI)
        n.triples.append( (IRI_Node("rdf:type", None), parent_iri) )
        
        # add constraints
        # assuming these are all continuous characteristics. which shouldn't be assumed
        n.incomplete_triples.append( (IRI_Node("sio:hasMinValue", None), Literal_Node() ) )
        n.incomplete_triples.append( (IRI_Node("sio:hasMaxValue", None), Literal_Node() ) )
        
        return n
    
        # just return the correct blank node, but as a simple node interpreter
        # TODO: A better way to do this is to just make nodes have an interpreter element
    def make_simple_node_interpreter(self, matching, cell, parent_iri, search_pattern):
        """Helper function to make a node interpreter living in 'cell', matching tokens 'matching', of type 'parent_iri'
        
        Node interpreters are used when nodes are able to fill in their own triples using data from the surrounding cells.
        """
        
        n = Simple_Node_Interpreter(matching, cell, search_pattern)
        
        # add known triples (instanceof IRI)
        n.triples.append( (IRI_Node("rdf:type", None), parent_iri) )
        
        # add constraints
        # assuming these are all continuous characteristics. which shouldn't be assumed
        n.incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
        
        return n
    
# uses NCBO Annotator to classify tokens
class NCBO_Token_Classifier (Token_Classifier):
    """The NCBO_Token_Classifier classifies a token based on results returned from the NCBO Annotator.
    
    Specifically, it performs concept-matching: that is, given a term, it will return the concepts that
    match that specific term.
    
    In addition, it will perform ranking of these concepts. The ranking information is stored as metadata
    in cell["NCBO_results"], which is a ranked list of dicts.
    
    Attributes:
      onto_list (list): List of strings (ontology prefixes) to use
      classifiers_to_exclude (list): List of classifiers to use to filter out unwanted tokens
      
    """
    
    def __init__(self, use_lemmas=True, use_synsets=True):
        """Instantiate an NCBO_Token_Classifier
        
        Parameters:
          use_lemmas (bool, optional): True by default. Set to False to not use WordNet Lemmas
          use_synsets (bool, optional): True by default. Set to False to not use WordNet Synsets 
        """
        self.use_lemmas=use_lemmas
        self.use_synsets=use_synsets
        
        self.onto_list = ["SCO","CMO","HHEAR","DOID","LOINC","DRON","CHEBI","HP","MEDDRA","NCIT","IOBC"]
        self.lmtzr = WordNetLemmatizer()
        
        self.classifiers_to_exclude = [Free_Value_Token_Classifier(), Concept_Token_Classifier()]
    
    def api_call(self,text):
        """Wrapper to make the API call to the NCBO annotator
        
        Parameters:
          text (string): Text to send to the annotator
        
        Returns:
          list: list of dicts (json-parsed) corresponding to the annotator results.
        """
        
        return annotate_text.annotate(text,self.onto_list)
    
    def classify(self, token, cell):
        """Given a token from a cell, return a corresponding list of features.
        
        Parameters:
          token (string): The token to classify
          cell (dict): The cell this token is found in
          
        Returns:
          list : List of features. May have multiple features, or none at all.
        """
            
        # Only send request if there is SOME alphabetical character in the text
        skip = True
        for c in token:
            if c.isalpha():
                skip = False
                break
        if skip:
            return []
        
        # Only send request if this token does not already have some feature attached to it
        for c in self.classifiers_to_exclude:
            if len(c.classify(token,cell)) > 0:
                return []
            
        # Reserved terms (exclude):
        if token.upper() in ["AND","OR","OF","NO"]:
            return []
        
        # instead of just calling the API on the token
        # call the API on the every word in the phrase, plus add'l context variables
        # then check the annotations that were returned
        # filter out those that do NOT include the token
        # sort those that DO by priority
        # most likely, frequency of words
        
        #results = self.api_call(token)
        # should make this a pattern classifier instead
        # but just for testing:
        
        tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
        tokens = tokenizer.tokenize(cell["text"].upper())
        
        stripped = ""
        for tok in tokens:
            stripped+=tok+" "
        
        #print(stripped)
        
        #print(cell.keys())
        
        # contextualizer
        ptokens = []
        if cell["col_parent"] is not None:
            #print(cell["col_parent"]["text"])
            #print(cell["col_parent"]["tokens"])
            
            ptokens = tokenizer.tokenize(cell["col_parent"]["text"].upper())

            parent=""
            for ptok in ptokens:
                parent+=ptok+" "
            if len(parent) > 0:
                parent = parent[0:-1] #strip last space
                
            stripped = parent+" "+stripped+parent
            #print(parent)
            #print(stripped)
        
        results = self.api_call(stripped)
        
        must_have = [token.upper()]
        
        # and append synonyms, lemmas (via wordnet)
        wordnet_terms = []
        
        # lemmas:
        lmtzr = self.lmtzr
        if self.use_lemmas:
            lemmas = [lmtzr.lemmatize(token, pos ="n"),lmtzr.lemmatize(token, pos ="v"),lmtzr.lemmatize(token, pos ="a")]
        else:
            lemmas = []
        wordnet_terms = lemmas[:]
        
        # synsets:
        syns = wordnet.synsets(token)
        if not self.use_synsets:
            syns = []
        for s in syns:
            for lemma in s.lemmas():
                wordnet_terms.append(lemma.name())
                if len(wordnet_terms) > 8:
                    break
        
        #remove duplicates (check that it HASNT already included the same lemma in terms_to_check already (eg drugs = drug drug))
        wordnet_terms = list(dict.fromkeys(wordnet_terms))
        
        terms_to_check = ""
        for l in wordnet_terms:
            if l.upper() not in tokens+ptokens:
                must_have.append(l.upper())
                terms_to_check+=l+" "
                
        for r in results:
            r["match"] = r["annotations"][0]["text"]
            r["annotations"][0]["matchType"] = "NCBO-"+r["annotations"][0]["matchType"]
                
        #print("Lemmas/Synset:" ,terms_to_check)
        if terms_to_check != "":
            res_tcheck = self.api_call(terms_to_check)
            for r in res_tcheck:
                r["match"] = token.upper()
                if r["annotations"][0]["text"].lower() in lemmas:
                    r["annotations"][0]["matchType"] = "WORDNET-LEMMA,NCBO-"+r["annotations"][0]["matchType"]
                else:
                    r["annotations"][0]["matchType"] = "WORDNET-SYN,NCBO-"+r["annotations"][0]["matchType"]
            results += res_tcheck
                           
        # divide into dic based on number of terms
        freq_to_res = {}
        
        for r in results:
            term_found = False
            for term in must_have:
                if term.upper() in r["annotations"][0]["text"].upper().split():
                    term_found = True
                    break
            if not term_found:
                continue
            # number of matched words
            freq = len(r["annotations"][0]["text"].upper().split())
            # wordnet has a frequency of 0 for synonyms, 0.5 for lemmas
            if "WORDNET" in r["annotations"][0]["matchType"]:
                if "LEMMA" in r["annotations"][0]["matchType"]:
                    freq = 0.5
                else:
                    freq = 0
            if freq not in freq_to_res.keys():
                freq_to_res[freq] = []
            freq_to_res[freq].append(r)
            
        # then sort by ontology priority list
        results_sorted = []
        
        ontos_to_ids = {}
        
        for freq in sorted(freq_to_res, reverse=True):
            res_arr = freq_to_res[freq]
            for onto in self.onto_list:
                for r in res_arr:
                    if r["annotatedClass"]["links"]["ontology"].endswith(onto):
                        
                        concept_id=r["annotatedClass"]["@id"]
                        if onto not in ontos_to_ids:
                            ontos_to_ids[onto] = []
                        if concept_id in ontos_to_ids[onto]:
                            continue # a duplicate
                        ontos_to_ids[onto].append(concept_id)
                        
                        #print(r["annotations"][0]["text"]+" FREQ:",freq," ONTO:", onto)
                        results_sorted.append(r)        
        
        # what this temporary list will do:
        # provide a list of matches for the human-in-the-loop to choose from
        # eventually, a better format should be decided upon
        
        if "NCBO_results" not in cell:
            cell["NCBO_results"] = []
        cell["NCBO_results"].append( (token,results_sorted) )
        
        # return top choice for now
        # when HITL is implemented, this code should be replaced
        
        if len(results_sorted) > 0:
            r = results_sorted[0]
            n = Concept_Feature(cell, [token], r["annotatedClass"]["@id"], None, [IRI_Node("sco:SubjectCharacteristic", None)])
            if "NCBO_top_res" not in cell:
                cell["NCBO_top_res"] = IRI_Node(r["annotatedClass"]["@id"], None)
            return [n]
        
        return []