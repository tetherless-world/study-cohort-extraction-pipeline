# study-cohort-extraction-pipeline

The study cohort extraction pipeline is a system designed to extract study cohort information from tables within research publication PDFs, and assemble this information into knowledge graphs. The code contained within this repository accepts tabular data extracted from a PDF as input, transforms it into a knowledge graph, and outputs it as an RDF turtle file. For a quick start, see [Using the Pipeline](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/README.md#using-the-pipeline). 

## Overview

The pipeline consists of four main steps: 
1. Extraction from the PDF via the IBM Corpus Converstion Service. Although sometimes considered a stage of the pipeline, the IBM Corpus Conversion Service will have to be used separately to generate the files required for input. For information on the input files, see [Input specification](formats/input_data_structure.txt).
2. Reorganization of that data into a more suitable structure, called a 'tree table'. This part of the pipeline is performed by the ```make_tree_tables()``` function, in the [tree_table_extraction.py](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/Extraction/tree_table_extraction.py) module.
3. identification/classification of that data into knowledge graph elements. This is performed by the ```kg_builder``` class in [kg_builder.py](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/Extraction/kg_builder.py).
4. using the spatial and conceptual relationships present in the table to infer the semantic relationships between KG elements, and thus assembling the disparate KG elements into one whole. This is also performed by the ```kg_builder``` class in [kg_builder.py](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/Extraction/kg_builder.py).

The resulting graph structure can then be serialized into RDF Turtle (.ttl) files.

## Using the Pipeline

### Requirements

External packages required:
 - NLTK, the [Natural Language Toolkit](https://www.nltk.org/)
 - [RDFLib](https://github.com/RDFLib/rdflib)
 
In order to map most terms to ontology concepts, the pipeline uses the [NCBO Annotator](https://bioportal.bioontology.org/annotator) via BioPortal's REST API. To use this feature of the pipeline, you are required to supply a BioPortal REST API key. For instructions on how to get a key, follow the instructions here: [Getting an API key](https://bioportal.bioontology.org/help#Getting_an_API_key).

Once you have the API KEY, place it after "NCBO_API_KEY:" in [api_keys.json](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/Extraction/api_keys.json).

### Input data preparation

To begin using the pipeline, the first step is to prepare the data that will be used as input by the pipeline. By default, the input data for the pipeline is stored in the [data/input](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/data/input) directory. (Todo: Add how to change input data directory)

Currently, the pipeline uses data files in the JSON format output by the IBM [Corpus Conversion Service](https://www.ibm.com/blogs/research/2018/08/corpus-conversion-service/) as input. These files contain data that has been extracted from PDFs, including text segments that have been identified as originating from tables, and some information on the position and font/style of these text segments. We plan to add support for other PDF extraction formats in the future, but for now see [formats/input_data_structure.txt](formats/input_data_structure.txt) for information on the structure of the input data file.

### Getting started

For a Jupyter notebook file explaining how to use the pipeline to generate the output files, see [Runner.ipynb](Runner.ipynb).
