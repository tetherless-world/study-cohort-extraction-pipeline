from .tree_table_extraction import print_tree_tables
from .graph_framework import *
import csv
from os import path

stat_measure_constraint = Supertype_Constraint(IRI_Node("sco:StatisticalMeasure", None))

# helper function for setting text on the table object
# this way, we can see the annotations on parts of the table
# accept: table object (remember to loop thru and give ALL table objects)
def set_text(table, input_file, indent=0):
    csv_rows = []
    
    for colnum,cell in enumerate(table["fields"]):
        
        if len(cell["tokens"]) > 0:

            if "text_backup" not in cell:
                cell["text_backup"] = cell["text"]
            cell["text"] = cell["text_backup"]
            
            if "NCBO_results" in cell and colnum == 0:
                match_dic = {}
                ontos = {"SCO":[],"CMO":[],"HHEAR":[],"DOID":[],"LOINC":[],"DRON":[],"CHEBI":[],"HP":[],"MEDDRA":[],"NCIT":[],"IOBC":[]}
                for (term,results) in cell["NCBO_results"]:
                    indentation="  "*indent
                    print(term+":")
                    for r in results:
                        #print(r)
                        onto = r["annotatedClass"]["links"]["ontology"].rsplit('/', 1)[-1]
                        #matches = r["annotations"][0]["text"]
                        matches = r["match"]
                        match_type = r["annotations"][0]["matchType"]
                        if "WORDNET" in match_type:
                            matches+=" ("+r["annotations"][0]["text"]+")"
                        concept_id=r["annotatedClass"]["@id"]
                        if 'prefLabel' not in r["annotatedClass"]:
                            pref_label = ""
                        else:
                            pref_label= r["annotatedClass"]['prefLabel']
                        print("  ("+onto+") "+concept_id+" : "+pref_label+" ["+matches+", "+match_type+"]")
                        
                        matches = matches.replace("`","'")+"`"+match_type #+"`"+pref_label
                        
                        if matches not in match_dic:
                            match_dic[matches] = {"SCO":[],"CMO":[],"HHEAR":[],"DOID":[],"LOINC":[],"DRON":[],"CHEBI":[],"HP":[],"MEDDRA":[],"NCIT":[],"IOBC":[]}
                        if (concept_id,pref_label) not in match_dic[matches][onto]:
                            match_dic[matches][onto].append( (concept_id, pref_label) )
                    print()
                
                #if no matches found, print NO_MATCH
                if not match_dic:
                    match_dic["`NO_MATCH`"] = {}
                
                # filename | row text | matched text | ONT1:ID1 | ONT2:ID1 | ...
                # filename |          | matched text |          | ONT2:ID2 | ...
                for matches,ontos in match_dic.items():
                    loop = True
                    
                    spl = matches.split("`",2)
                    term = spl[0]
                    match_type = spl[1]
                    #pref_label = spl[2]
                    
                    while(loop):
                        loop = False
                        csv_row = [input_file,indentation+cell["text_backup"], match_type, term ]
                        for onto, ids in ontos.items():
                            if len(ids) != 0:
                                cid, pref_label = ids.pop(0)
                                csv_row.append(pref_label+": "+cid)
                            else:
                                csv_row.append("")
                            if len(ids) != 0:
                                loop = True
                        csv_rows.append(csv_row)
                        #print(csv_row)
            
            cell["text"] = ""
            for (t,f_array) in cell["tokens"]:
                cell["text"] +=" ["+t
                if len(f_array) > 0: cell["text"] +=":"
                for f in f_array:
                    if f.get_type() == FeatureType.VALUE:
                        
                        # for evaluation:
                        # row header, col #, reported value, actual value, reported measure, actual measure, char label, actual label
                        if colnum is not 0 and isinstance(f,Free_Value):
                            header = table["fields"][0]["text"]
                            # get value
                            value = f.value
                            # get measure, characteristic
                            measure = ""
                            char = ""
                            for f in f_array:
                                if isinstance(f, Node_Instance):
                                    # check type
                                    if stat_measure_constraint.is_supertype_of(f):
                                        measure = f.triples[0][1].to_string()
                                    else:
                                        char = f.to_string()
                            # row header, col #, reported value, actual value, reported measure, actual measure, char label, actual label, spans
                            #csv_rows.append([header,colnum,value,0,measure,0,0,char,str(cell["spans"])])
                        cell["text"]+=" "+str(f.to_string())
                        
                    if f.get_type() == FeatureType.INTERPRETER:
                        cell["text"]+=" "+str(f.to_string())
                cell["text"]+="]"
    for subtable in table["records"]:
        csv_rows += set_text(subtable,indent+1)
    
    return csv_rows


def print_visualization(data, input_file, output_dir=None):
    ''' Print a visualization and a results file for the data.
    
        Filepath generated from input_file. 
        Directory of input_file is used unless output_dir is provided.
    '''
    
    csv_rows = []
    for t in data["tables"]:
        csv_rows += set_text(t, input_file)

    if output_dir is None:
        output_dir = path.dirname(input_file)
    viz_fn = output_dir+"/out."+path.basename(input_file)[0:30]+".txt"
    csv_fn = output_dir+"/results."+path.basename(input_file)[0:30]+".csv"
        
    print_tree_tables(data, viz_fn)

    with open(csv_fn, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for row in csv_rows:
            writer.writerow(row)

    print("Saved csv file to ",csv_fn)
