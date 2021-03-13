# helper function for building the graph
# used on a table object to translate the annotations into RDF components, and append them to the supplied graph object

from rdflib import Graph, URIRef
import annotate_text.get_semantic_types
from os import path

def add_table_to_graph(table, g):
    
    for cell in table["fields"]:
        if "column" in cell:
            for f in cell["column"]:
                f.translate(g)

def convert_to_rdflib(data):
    
    g = Graph()
    for t in data["tables"]:
        add_table_to_graph(t, g)
    return g

def print_graph(data, input_file, output_dir = None):
    ''' Serialize data to an RDF file.
    
        Filepath generated from input_file. 
        Directory of input_file is used unless output_dir is provided.
    '''

    g = convert_to_rdflib(data)
    
    # ensure correct prefixes
    g.namespace_manager.bind('sio', URIRef("http://semanticscience.org/resource/"))
    g.namespace_manager.bind('sco', URIRef("https://idea.tw.rpi.edu/projects/heals/studycohort/"))
    g.namespace_manager.bind('sco-i', URIRef("https://idea.tw.rpi.edu/projects/heals/studycohort_individuals/"))
    g.namespace_manager.bind('owl', URIRef("http://www.w3.org/2002/07/owl#"))

    if output_dir is None:
        output_dir = path.dirname(input_file)
    g_fn = output_dir+"/gra."+path.basename(input_file)[0:30]+".ttl"
    
    g.serialize(g_fn,format='turtle')

    print("Saved KG serialization to ",g_fn,"\n")