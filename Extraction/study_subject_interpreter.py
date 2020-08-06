#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The Study Subject interpreter class

Used to perform the recursive assembly within Step 4 of the pipeline (KG assembly)
"""
from .graph_framework import *

# This interpreter just tries to match to the study subject template,
# TODO in future, make more general
class Study_Subject_Interpreter (Interpreter):
    """The Study Subject Interpreter operates on a column within a table to assemble a Study Subject instance.
    
    The Study Subject Interpreter recursively moves through the tree table structure assembled in step 2
    of the pipeline according to a depth-first-search manner. In this way, it combines node instances together,
    matching values to measures and measures to characteristics, until eventually characteristics are all returned
    as attributes to the top-level study subject individual.
    
    Additionally, categorical variables (which are themselves Study Subjects) are identified via a number of
    heuristics and returned as their own top-level individuals.
    
    Attributes:
      kg_builder (kg_builder): A pointer to the interpreter's kg_builder
      base (Individual_Instance): The instance being built by this Interpreter
      
    """
    # All other attributes are considered private and subject to change
    # In future, default cat, cont types should be configurable attributes, as well as signifiers, etc.
    # This class is a bit of a mess, would be good to refactor it
    
    # interpret this cell- well, starting from this cell and moving its way through all the children
    def interpret(self, cell):
        """Modify the cell by assembling its features into a composite or tree-like structure.

            Parameters:
              cell (dict): Cell to interpret.
        """
        
        # to start: assume this cell is a column header
        # based on that, try to determine study arm name/other info
        arm_name = self.get_arm_name(cell)
        arm_iri = self.get_arm_name(cell)+"StudyArm"
        
        # make a study subject blank node to use as a base, and to live in this cell
        
        #n = Node_Instance([], cell)
        n = Individual_Instance([], cell, arm_iri, "https://idea.tw.rpi.edu/projects/heals/studycohort_individuals/")
        n.triples.append((IRI_Node("rdf:type", None), IRI_Node("owl:Class", None)) )
        n.triples.append((IRI_Node("rdfs:subClassOf", None), IRI_Node("sio:StudySubject", None)) )
        # label w metadata (TODO: fix. obvs we needs string datatype. plus actual label IRI)
        n.triples.append((IRI_Node("rdfs:hasLabel", None),  Free_Value(cell["tokens"], cell, cell["text"])))
        # TODO SOON: something about intervention arm vs. non-intervention-arm
        n.incomplete_triples.append((IRI_Node("sio:hasAttribute", None), Supertype_Constraint(IRI_Node("sco:PopulationSize", None))  ))
        
        self.base = n
                                 
            
        self.age_found = False
        self.use_open_paren = True
            
        # TODO: Specify elsewhere
        
        # TODO: Each of these default value types should have a confidence metric associated with it in the node instance
        # based on closeness, so 'default' is lowest confidence, while immediate row header (or same cell?) is highest
        # could be INF for default, 0 for same-row, 1,2,3... for every row thereafter? Sounds good to me
        
        self.default_cont_types = [Node_Instance(["_default"],cell), Node_Instance(["_default"], cell)]
        self.default_cont_types[0].triples.append( (IRI_Node("rdf:type", None), IRI_Node("sio:Mean", None)) )
        self.default_cont_types[0].incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
        self.default_cont_types[1].triples.append( (IRI_Node("rdf:type", None), IRI_Node("sio:StandardDeviation", None)) )
        self.default_cont_types[1].incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
        
        self.default_cat_types = [Node_Instance(["_default"],cell), Node_Instance(["_default"], cell)]
        self.default_cat_types[0].triples.append( (IRI_Node("rdf:type", None), IRI_Node("sco:PopulationSize", None)) )
        self.default_cat_types[0].incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
        self.default_cat_types[1].triples.append( (IRI_Node("rdf:type", None), IRI_Node("sio:Percentage", None)) )
        self.default_cat_types[1].incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
                        
        # start w/ default cont types
        # as well as including a reference to this study arm (edit-- this didnt seem to work)
        defaults = self.default_cont_types#+[self.base]
            
        # now... recurse!
        all_features = self.rec_interpret(cell, defaults)
        # all_features now has all features from this column in a tree-like data structure
        
        #TODO Refactor the below. Should be in rec_interpret somehow?
        
        # lastly, fill in the base
        # this append triple is added as needed
        append_triple = ((IRI_Node("sio:hasAttribute", None), Supertype_Constraint(IRI_Node("sco:SubjectCharacteristic", None)) )) 
        # also add categoricals
        cell["column"] = []
        for f in all_features:
            #TODO investigate
            if f.get_type() is FeatureType.VALUE:
                
                if append_triple[1].is_supertype_of(f):
                    self.base.incomplete_triples.append(append_triple)
                    self.base.try_fill(f, len(self.base.incomplete_triples) - 1)
                        # TODO: mark f as subsumed, somehow
                        # TODO: toks from the column marked with f?
                        #TODO: old feature on t should get subsumed 
                else:               
                    # still try to fill each triple
                    for i,t in enumerate(self.base.incomplete_triples):
                        self.base.try_fill(f, i)
                            # TODO: mark f as subsumed, somehow
                            # TODO: toks from the column marked with f?
                            #TODO: old feature on t should get subsumed 
            if not f.is_subsumed:                
                cell["column"].append(f)
                

        # now base has what we need
        # mark anyway though
        cell["column"] = [self.base]+cell["column"]
                                    
    # recurse through columnal children, but with specific attributes to fill
    # return top-level attribute(s) of this cell
    def rec_interpret(self, data_cell, attributes):
        """Recursive helper function for interpret.

            Parameters:
              data_cell (dict): Cell to interpret.
              attributes (list): List of features to search for / try to use to fill

            Returns:
              list : List of features within this cell that have /not/ been subsumed
        """
        
        # first, interpret row header (in future this should be a specific thing)
        # TODO: not good to use indexing like this
        header_cell = data_cell["row"]["fields"][0] 
        
        # see if any features in the header cell match these
        cont_supertypes = [ Supertype_Constraint(IRI_Node("sco:CentralTendencyMeasure", None)), Supertype_Constraint(IRI_Node("sco:DispersionMeasure", None)) ]
        cat_supertypes = [ Supertype_Constraint(IRI_Node("sco:PopulationSize", None)), Supertype_Constraint(IRI_Node("sio:Percentage", None)) ]
        new_cat_attr = []
        
        # attributes to be inherited
        att_orig = None # will be manually copied later unless copied in a specific way
                             
        for (tok,features) in header_cell["tokens"]:
            
            for f in features:
                # tbh this if statement is itself unnec
                # really what it SHOULD be is interpreter-only but I have some interpreters misclassified as value-type
                if f.get_type() is FeatureType.VALUE or f.get_type() is FeatureType.INTERPRETER: 
                    
                    # try to match each supertype
                    for i,supertype in enumerate(cont_supertypes):
                        if supertype.is_supertype_of(f):
                            # remember
                            # TODO: Currently overwrites older thing here. Shouldn't do that-- what if more than 1 in cell?
                            # TODO: using indexing like this is p bad, should refactor to be class-based
                            attributes[i] = f
                    for i,supertype in enumerate(cat_supertypes):
                        if supertype.is_supertype_of(f):
                            # if %: just use default % in case this one is contaminated
                            # TODO: Fix % so it doesn't become contaminated (e.g. search_pattern needs to be improved)
                            if i == 1:
                                f = Node_Instance([tok],header_cell)
                                f.triples.append( (IRI_Node("rdf:type", None), IRI_Node("sio:Percentage", None)) )
                                f.incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
                            new_cat_attr.append(f)
        
        # age is a "signifier"
        # if age is here, we infer information (specifically whether to classify all "("-containing cells as categorical )
        has_age = False
        if not self.age_found and "age" in header_cell["text"].lower():
            has_age = True
            self.age_found = True

            if "(" in data_cell["text"] and not "±" in data_cell["text"]:
                age_has_cont_non_default = False
                for a in attributes:
                    for i,supertype in enumerate(cont_supertypes):
                        if supertype.is_supertype_of(a) and "_default" not in a.matching:
                            age_has_cont_non_default = True
                            break
                if not age_has_cont_non_default:
                    # dont use open paren, since age would have been misclassified
                    self.use_open_paren = False
        
        # for this row:
        # create a subject characterstic (to be added as attribute) or just interpret as single value?
        # thoughts: 1. we need a characteristic to be toplevel
        # 2. we need mean, median, etc. by themselves to, well, return themselves
        # 3. mean, median with other stuff generally becomes characteristic as well.
            
        if True:
            # Try to determine if this cell contains a continuous or a categorical characteristic
            # and if so, make the template for that characteristic
            
            # thoughts:
            # "attributes" contains:
            #    1. newly discovered attributes from this row header cell
            #    2. old-ly discovered attributes from previous row subheaders
            #    3. default (cont char) attributes (indicated with "_default" as their matching keyword)
            # "new_cat_attr" contains: 
            #    1. n-type or %-type from this row header cell
            #  so:
            #  If there are cat-type attributes, they should not be mixed with other types of attributes
            #    so, don't mix cat-type with default cont-type (override them with default for cat)
            #    however, since % can be a unit, try to override % with non-default cont-types if able
            #  If the data cell contains ±, then it should be cont-type. 
            #  If it contains only 1 eligible feature to be subsumed, don't subsume that feature into a
            #    default attribute when a learned attribute can be used instead
            #   ---> this rule should be used when actually trying to fill. don't do that here, because
            #        these attributes are passed on
            
            # first: determine if attributes contains anything categorical
            # and determine if default continuous attributes are in play
            cat_att = [None,None]
            def_cont_att = [None,None]
            for a in attributes:
                for i,supertype in enumerate(cat_supertypes):
                    if supertype.is_supertype_of(a):
                        cat_att[i] = a
                for i,supertype in enumerate(cont_supertypes):
                    if supertype.is_supertype_of(a) and "_default" in a.matching:
                        def_cont_att[i] = a
            # and combinate with new_cat_attr
            # yes this is redundant. TODO: Refactor
            for a in new_cat_attr:
                for i,supertype in enumerate(cat_supertypes):
                    if supertype.is_supertype_of(a):
                        cat_att[i] = a
            
            # check for ± symbol in data_cell
            plus_or_minus = False
            for (tok,_) in data_cell["tokens"]:
                if "±" in tok:
                    plus_or_minus = True
                    break
                    
            # check for % symbol in data_cell
            percent_symbol = False
            for (tok,_) in data_cell["tokens"]:
                if "%" in tok:
                    percent_symbol = True
                    break
                    
            # check for ( symbol in data_cell
            # supply default cat att if using continuous characteristics AND format is x (y)
            open_paren = False
            if cat_att[1] is None and cat_att[0] is None and def_cont_att[0] is not None and def_cont_att[1] is not None and not plus_or_minus and self.use_open_paren:
                for (tok,_) in data_cell["tokens"]:
                    if "(" in tok:
                        #treat as a weaker version of %
                        new_percent_node = Node_Instance([tok],data_cell)
                        new_percent_node.triples.append( (IRI_Node("rdf:type", None), IRI_Node("sio:Percentage", None)) )
                        new_percent_node.incomplete_triples.append( (IRI_Node("sio:hasValue", None), Literal_Node() ) )
                        att_orig = attributes[:]
                        cat_att[1] = self.default_cat_types[1]
                        cat_att[0] = self.default_cat_types[0]
                        open_paren = True
                        break
            
            is_cat_char = False
            # is new_cat_attr non-empty or does attributes contain anything categorical?
            if cat_att[0] is not None or cat_att[1] is not None:
            # if so:
            #   do we have the required study population attribute?
                if cat_att[0] is not None:
                    is_cat_char = True
                    # provide the default secondary measure (%) IF there is no plus or minus (TODO)
                    attributes[0] = cat_att[0]
                    if cat_att[1] is None:
                        attributes[1] = self.default_cat_types[1]
                    else:
                        attributes[1] = cat_att[1]
            #   if not, then all we have is % (as cat_att[1] is not None)
            #   is the central tendency default? AND is there NOT a ± in the data cell?
                elif def_cont_att[0] is not None and not plus_or_minus:
                    is_cat_char = True
                    # in that case, override default continuous central with the default primary measure (no.)
                    attributes[0] = self.default_cat_types[0]
                    attributes[1] = cat_att[1]
                else:
            #     if not: assume % is unit problem is taking place. is_cont_char = true. 
                  is_cat_char = False
            #     TODO: override any categorical with learned continuous. For now just use default I suppose
                  #if def_cont_att[1] is not None: 
                  #  attributes[1] = self.default_cont_types[1]
                  # Thinking about the above made me think it doesn't make sense-- after all, doesn't the attribute already contain the old continuous characteristic? 
                  # What we should address is the edge case of a row subheader with no (%) and a child with mean (SE), but I think that should already work with what we have here. TODO: Investigate/test
                    
            # In the case that BOTH cat_atts are empty:
            # If "%" is found within the cell, it has already been interpreted and will be added as an attribute
            # the important part is making sure population size is also accounted for, and ensuring the characteristic is categorical
            elif percent_symbol:
                # overriding default bc the % was found in the data cell, not the header
                att_orig = attributes[:]
                attributes[0] = self.default_cat_types[0]
                is_cat_char = True
                
        # Do a loop through tokens in the header cell to determine whether this cell should contain a characteristic
        # tokens that are an indicator of a characteristic are added to good_tokens
        # 2./3. Best way to do this is: assemble a list of tokens which are A. non-entirely numerical, B. not associated with stat measure features. If any jump out, use those for the label, even if we don't know specifics.
                        
        good_tokens = []
        for (tok, features) in header_cell["tokens"]:
            if tok.isalnum():
                bad = False
                for f in features:
                    if isinstance(f, Literal_Node) or Supertype_Constraint(IRI_Node("sco:StatisticalMeasure", None)).is_supertype_of(f): 
                        bad = True
                if not bad: good_tokens.append(tok)
        
        if len(good_tokens) > 0:
            
            # indicates that we will try to create a characteristic for this cell 
            has_char = True
            
            # make categorical characteristic
            if is_cat_char:
                cat_iri = "Row"+str(data_cell["spans"][0][0])+self.arm_name+"StudySubject"
                n = Individual_Instance(good_tokens[:], data_cell, cat_iri, "https://idea.tw.rpi.edu/projects/heals/studycohort_individuals/")
                n.triples.append((IRI_Node("rdf:type", None), IRI_Node("owl:Class", None)) )
                n.triples.append((IRI_Node("rdfs:subClassOf", None), self.base))
                
                # lets just say 1 pop size and 1 % for now
                n.incomplete_triples.append((IRI_Node("sio:hasAttribute", None), Supertype_Constraint(IRI_Node("sco:PopulationSize", None))  ))
                n.incomplete_triples.append((IRI_Node("sio:hasAttribute", None), Supertype_Constraint(IRI_Node("sio:Percentage", None)) ))
                n.triples.append((IRI_Node("rdfs:hasLabel", None),  Free_Value(good_tokens[:], header_cell, " ".join(good_tokens))))
                
            else:
                # make cont characteristic (is_cont_char means this cell is marked as containing such)
                is_cont_char = True
                n = Node_Instance(good_tokens[:],data_cell)

                # this is to prevent filling this constraint with a node instance, instead of an IRI
                c = Supertype_Constraint(IRI_Node("sco:SubjectCharacteristic", None))
                c.can_be_node_instance = False
                
                # If a concept has been identified
                if "NCBO_top_res" in header_cell.keys():
                    c = header_cell["NCBO_top_res"]
                    n.triples.append((IRI_Node("rdf:type", None), c ))
                else:
                    n.incomplete_triples.append((IRI_Node("rdf:type", None), c ))

                # TODO TODAY: unit work
                n.incomplete_triples.append((IRI_Node("sio:hasUnit", None), Supertype_Constraint(IRI_Node("sco:UnitOfMeasurement", None)) ))

                # lets just say 1 central statistical measure and 1 dispersion measure
                n.incomplete_triples.append((IRI_Node("sio:hasAttribute", None), Supertype_Constraint(IRI_Node("sco:CentralTendencyMeasure", None)) ))
                n.incomplete_triples.append((IRI_Node("sio:hasAttribute", None), Supertype_Constraint(IRI_Node("sco:DispersionMeasure", None)) ))
                n.triples.append((IRI_Node("rdfs:hasLabel", None),  Free_Value(good_tokens[:], header_cell, " ".join(good_tokens))))
                                    
        else:
            has_char = False
        
        # duplicate (using feature.duplicate, not deepcopy or something)
        if att_orig is None:
            att_orig = attributes[:]
        for i,f in enumerate(attributes):
            attributes[i] = f.duplicate(data_cell)
        
        
        #for a in attributes:
            #print("ATT ",a.to_string())
        
        # next task is fairly simple
        # just try to fill each hole (in a triple)
        
        att_to_return = []
                          
        # first fill the triples that are needed by attributes
        # we do a preliminary pass to prioritize learned attributes over defaults
        # but we still want order preserved, so only prioritize if some attributes are left unfilled
        num_to_fill = 0 # number of FEATURES that will fill a triple
        will_be_subsumed = [] # features that will get subsumed
        for a in attributes:
            for (tok,features) in data_cell["tokens"]:
                #  If it contains only 1 eligible feature to be subsumed, don't subsume that feature into a
                #    default attribute when a learned attribute can be used instead
                for f in features:
                    if f.get_type() is FeatureType.VALUE and f not in will_be_subsumed:
                        # can we fill triple
                        for i,t in enumerate(a.incomplete_triples):
                            if a.can_fill(f, i):
                                num_to_fill+=1
                                will_be_subsumed.append(f)
                                break
                                
        # now, count the number of incomplete triples that can become complete with at least one feature
        fillable_triples = []
        for a in attributes:
            for i,t in enumerate(a.incomplete_triples):
                for f in will_be_subsumed:
                    if t not in fillable_triples and a.can_fill(f, i): 
                        fillable_triples.append(t)
                    
                
                                
        fill_defaults = True
        #print("NtF: ",num_to_fill,"WbS: ", will_be_subsumed, "FT: ",fillable_triples)

        # instead of len(attributes)
        # should be len(fillables WITHIN attributes)
        # note: owl:class, etc. are NOT fillables and should be excluded from this count
        # TODO
        if num_to_fill < len(fillable_triples) and num_to_fill > 0:
            # now we have a problem: its possible a default central tendency will be filled instead of a learned dispersion measure
            # TODO: Use an actual confidence metric here, such that higher subheaders are similarly de-prioritized
            # for now I'm just de-prioritizing defaults
            # note: if ALL attributes are default, then we should still fill defaults. its only if one is default that we de-prioritize it
            for a in attributes:
                if "_default" not in a.matching:
                    fill_defaults = False
                    break

        for a in attributes:
            if not fill_defaults and "_default" in a.matching:
                #skip over this default
                continue
            for (tok,features) in data_cell["tokens"]:
                
                for f in features:
                    if f.get_type() is FeatureType.VALUE and not f.is_subsumed:
                        
                        # try to fill each triple in the attribute
                        for i,t in enumerate(a.incomplete_triples):
                            
                            #if not fill_defaults:
                                #print("Triple ",i,": ",t,", for ",f)
                            
                            if a.try_fill(f, i):
                                # In try_fill, f is marked as subsumed, somehow
                                    
                                # here tok is marked with f
                                features.append(a)
                                att_to_return.append(a)
                                break
                
            # try self.base now
            # (note that self.base gets marked as subsumed but can still be used)
            for i,t in enumerate(a.incomplete_triples):
                a.try_fill(self.base, i)
             
                                    
        # now fill n's triples using the attributes we pulled out earlier and just filled
        # This should really be a function... try_fill_all? TODO
        if has_char: # if there are triples to fill

            for f in att_to_return:
                if f.get_type() is FeatureType.VALUE and not f.is_subsumed:

                    # try to fill each triple
                    for i,t in enumerate(n.incomplete_triples):
                        if n.try_fill(f, i):
                            # TODO: mark f as subsumed, somehow

                            # here, tok that has f is marked with f
                            for (original_tok, features) in f.cell["tokens"]:
                                    for f_tok in f.matching:
                                        if f_tok is original_tok:
                                            features.append(n)
                            break
            # now that we have done all we can to fill this newly created characteristic
            # we can put this in the att_to_return array (but clear it first?)
            att_to_return = [n]
        # else: just return the measures that are already in att_to_return
        
        # iterate thru kids
        # assemble their returned values like voltron      
        for child_cell in data_cell["col_children"]:                       
            child_features = self.rec_interpret(child_cell, att_orig[:])
            
            # if this cell has a cont char to fill: (TODO not great name for that variable)
            if has_char:
                # do the child's features help with the adult?
                # note that n may have "type <a sco:SubjectCharacteristic>", which could also be a problem if the child features are that
                for f in child_features:
                    filled_adult = False
                    if f.get_type() is FeatureType.VALUE and not f.is_subsumed:

                        # TODO eval child return type

                        # try to fill each triple
                        for i,t in enumerate(n.incomplete_triples):
                            if n.try_fill(f, i):
                                filled_adult = True
                                # TODO: mark f as subsumed, somehow

                                # here, tok that has f is marked with f
                                for (original_tok, features) in f.cell["tokens"]:
                                        if tok is original_tok:
                                            features.append(n)
                                break
                        # now add metadata/label:
                        if isinstance(f,Node_Instance):
                            # check for pre-existing label:
                            no_label_found = True
                            lb = " ".join(good_tokens)
                            for triple in f.triples:
                                    if triple[0].IRI_String is "rdfs:hasLabel":
                                        no_label_found = False
                                        # remove the old triple
                                        f.triples.remove(triple)
                                        # make new label
                                        triple[1].value += ", "+lb
                                        triple[1].matching += good_tokens
                                        # re-add triple, so as to keep old matching as well as have new
                                        f.triples.append((IRI_Node("rdfs:hasLabel", None),  triple[1]))
                                        # TODO: Update the tokens in this cell to have relevent matching/feature
                                        break
                            if no_label_found:
                                f.triples.append((IRI_Node("rdfs:hasLabel", None), Free_Value(good_tokens,header_cell,lb)))
                                    
                                    
                    # if this feature could not fill adult, just append it as an additional TLF (top-level-feature)
                    if not filled_adult:
                        att_to_return.append(f)
                                    
            # if this cell has nothing to fill:
            else:
                att_to_return += child_features
        
        # return top-level (non-subsumed) features of this cell
        # this should be done with a dedicated data structure for tokens:
            # each token is the leaf of a tree. follow the tree "upwards" until you get to the "root"(s)
            # and return those roots
        # for now we just make sure there are no free values left in this cell
        
        for (tok,features) in data_cell["tokens"]:
            if len(features) is 1 and features[0] not in att_to_return:
                att_to_return += features
                
        # now att_to_return should have top-level features from this cell and its children
        return att_to_return
    
    def get_arm_name(self, cell):
        """Generate a name for the study arm based on this cell

            Parameters:
              cell (dict): Cell to use for the name.
              
            Returns:
              string: New name
        """
        
        self.arm_name = ""
        #for (tok, features) in cell["tokens"]:
        #        self.arm_name = self.arm_name + cleanForIRI(tok).capitalize()
        self.arm_name = "Col"+str(cell["spans"][0][1])+"Table"+str(cell["table_num"])
        return self.arm_name