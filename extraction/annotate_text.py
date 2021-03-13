import urllib.request, urllib.error, urllib.parse
import json
import os
from pprint import pprint

from time import sleep

REST_URL = "http://data.bioontology.org"
NCBO_API_KEY = ""
API_KEY_FILE = "./api_keys.json"

def get_json(url):
    global NCBO_API_KEY
        
    opener = urllib.request.build_opener()
    
    if NCBO_API_KEY is "":
        NCBO_API_KEY = load_api_key()
    opener.addheaders = [('Authorization', 'apikey token=' + NCBO_API_KEY)]
    return json.loads(opener.open(url).read())

def load_api_key():
    
    with open(API_KEY_FILE) as f:
        data = json.load(f)
    return data["NCBO_API_KEY"]

def print_annotations(annotations, get_class=True):
    for result in annotations:
        class_details = result["annotatedClass"]
        if get_class:
            try:
                class_details = get_json(result["annotatedClass"]["links"]["self"])
            except urllib.error.HTTPError:
                print(f"Error retrieving {result['annotatedClass']['@id']}")
                continue
        print("Class details")
        print("\tid: " + class_details["@id"])
        print("\tprefLabel: " + class_details["prefLabel"])
        print("\tontology: " + class_details["links"]["ontology"])

        print("Annotation details")
        for annotation in result["annotations"]:
            print("\tfrom: " + str(annotation["from"]))
            print("\tto: " + str(annotation["to"]))
            print("\tmatch type: " + annotation["matchType"])

        if result["hierarchy"]:
            print("\n\tHierarchy annotations")
            for annotation in result["hierarchy"]:
                try:
                    class_details = get_json(annotation["annotatedClass"]["links"]["self"])
                except urllib.error.HTTPError:
                    print(f"Error retrieving {annotation['annotatedClass']['@id']}")
                    continue
                pref_label = class_details["prefLabel"] or "no label"
                print("\t\tClass details")
                print("\t\t\tid: " + class_details["@id"])
                print("\t\t\tprefLabel: " + class_details["prefLabel"])
                print("\t\t\tontology: " + class_details["links"]["ontology"])
                print("\t\t\tdistance from originally annotated class: " + str(annotation["distance"]))

        print("\n\n")

                          
def annotate(text, ontologies):
    ''' Returns the results of the NCBO annotator on text, when limited to the ontologies in ontologies (list of strings).'''
                          
    if ontologies is None:
        return  get_json(REST_URL + "/annotator?text=" + urllib.parse.quote(text))
    
    o_ids = ""
    for o_id in ontologies:
        o_ids = o_ids+o_id+","
    sleep(0.08)
    print("REQ: "+text)
    return  get_json(REST_URL + "/annotator?include=prefLabel&text=" + urllib.parse.quote(text) + "&ontologies=" + o_ids)
       
def post(url,data):
    global NCBO_API_KEY
                          
    parsed_data = urllib.parse.urlencode(data).encode()
    req =  urllib.request.Request(url, data=parsed_data) # this will make the method "POST"
                          
    opener = urllib.request.build_opener()

    if NCBO_API_KEY is "":
        NCBO_API_KEY = load_api_key()
    opener.addheaders = [('Authorization', 'apikey token=' + NCBO_API_KEY),('Content-Type', 'application/json'),('Accept', 'application/json')]
    return json.loads(opener.open(req).read())
                          
def get_semantic_types(results):
    
    # build batch request
    collection = []
    for r in results:
        c = {"class":r["annotatedClass"]["@id"], "ontology":r["annotatedClass"]["links"]["ontology"]}
        collection.append(c)
    data = {"http://www.w3.org/2002/07/owl#Class": {"collection":collection,"display": "semanticTypes"}}
                          
    # use batch endpoint
    sleep(0.08)
    print("BATCH REQ")
    post(REST_URL+"/batch",data)
                          
def example():
    text_to_annotate = "Melanoma is a malignant tumor of melanocytes which are found predominantly in skin but also in the bowel and the eye."

    # Annotate using the provided text
    annotations = get_json(REST_URL + "/annotator?text=" + urllib.parse.quote(text_to_annotate))

    # Print out annotation details
    print_annotations(annotations)

    # Annotate with hierarchy information
    annotations = get_json(REST_URL + "/annotator?max_level=3&text=" + urllib.parse.quote(text_to_annotate))
    print_annotations(annotations)

    # Annotate with prefLabel, synonym, definition returned
    annotations = get_json(REST_URL + "/annotator?include=prefLabel,synonym,definition&text=" + urllib.parse.quote(text_to_annotate))
    print_annotations(annotations, False)