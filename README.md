# Evaluation Results

This branch holds the final results of evaluating the study cohort extraction pipeline, as well as the code used to generate that results data. As new results data is generated, additional commits are added to this branch with the new data and the new version of the code used to generate said data. The raw I/O data, which contains text pulled from published journal articles, is not currently included with this data so as to avoid potential intellectual property conflicts, but if you email me at frankj6 <at> rpi <dot> edu I can provide you with data if you have access to the journal articles used for the evaluation. We provide the following data in this repository:

## Semantic alignment evaluation results

The semantic evaluation evaluated the performance of the pipeline's alignment of plaintext biomedical terms, found in table row headers, to the corresponding concepts in ontologies. 

We provide the following files in the **concept_data_results** directory:
- **results.txt**: The summary statistics computed for each ontology
- **evaluation_procedure.txt**: A document containing a description of the evaluation process and specific guidelines for our human annotators.
- **exclusions.txt**: The list of words excluded from the evaluation when creating the current version of **results.txt**.
- **Evaluation.ipynb**: The evaluation code, at the time **results.txt** was created.
