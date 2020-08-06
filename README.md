# study-cohort-extraction-pipeline

The study cohort extraction pipeline is a system designed to extract study cohort information from tables within PDFs, and assemble this information into knowledge graphs. The code contained within this repository accepts tabular data extracted from a PDF as input, transforms it into a knowledge graph, and outputs it as an RDF turtle file. For a quick start, see [Using the Pipeline](https://github.com/tetherless-world/study-cohort-extraction-pipeline/blob/master/README.md#quick_start).

## Overview

The pipeline consists of four main steps: 
1. extraction from the PDF via the IBM Corpus Converstion Service
2. reorganization of that data into a more suitable structure, called a 'tree table'
3. identification/classification of that data into knowledge graph elements
4. using the spatial and conceptual relationships present in the table to infer the semantic relationships between KG elements, and thus assembling the disparate KG elements into one whole.

The resulting graph structure can then be serialized into RDF Turtle (.ttl) files.

## Using the Pipeline
