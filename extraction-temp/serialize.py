# helper function for building the graph
# used on a table object to translate the annotations into RDF components, and append them to the supplied graph object

from rdflib import Graph, URIRef

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

def print_graph(data, input_file):

    g = convert_to_rdflib(data)
    
    # ensure correct prefixes
    g.namespace_manager.bind('sio', URIRef("http://semanticscience.org/resource/"))
    g.namespace_manager.bind('sco', URIRef("https://idea.tw.rpi.edu/projects/heals/studycohort/"))
    g.namespace_manager.bind('sco-i', URIRef("https://idea.tw.rpi.edu/projects/heals/studycohort_individuals/"))
    g.namespace_manager.bind('owl', URIRef("http://www.w3.org/2002/07/owl#"))

    g_fn = "./gra."+input_file[2:30]+".ttl"
    g.serialize(g_fn,format='turtle')

    print("Saved KG serialization to ",g_fn,"\n")