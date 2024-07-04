# Base Prompt
graph_info = """
                ### Contextual Intro
                ArangoDB graph DB represents a biomedical entity network, structured with nodes & edges, each carrying biomedical data types. Nodes = entities like proteins, drugs, diseases, genes. Edges = relationships/interactions. Aim: facilitate complex queries for insights into drug discovery, disease understanding, bio research.

                ### Node Struct
                - **Sample Node**: `node_sample` JSON shows a protein node. Elements:
                - IDs: `_key`, `_id`, `_rev`.
                - `type`: "Protein".
                - `labels`: ["Protein"].
                - `properties`: Dict of relevant properties, e.g., `identifier` ("A0A1B0GTW7"), `gene`, `description`, `org_ncbi_id`, `name`, etc.

                ### Edge Struct
                - **Sample Edge**: `edge_sample` JSON. Elements:
                - IDs: `_key`, `_id`, `_rev`.
                - Connects: `_from`, `_to`.
                - `label`: Type of relationship, e.g., "INCLUDES_PCiC".
                - `properties`: Edge attributes, like `license`, `source`, `vestige`, `forward_degrees`, etc.
                - Nodes: `start`, `end` with their properties.

                ### Edge Labels
                - Variety of labels for relationship types, e.g., `ADVRESPONSE_TO_mGarC`, `ASSOCIATES_DaG`, etc.
                - Each label, like `INCLUDES_PCiC`, signifies a specific interaction or association.
                - Crucial for query construction; guide graph traversal linking entities.

                ### Aim
                By understanding node/edge structure & labels, construct effective AQL queries for exploring bio networks, uncovering insights in drug-target interactions, gene-disease associations, etc.

            """

available_edge_labels = """ADVRESPONSE_TO_mGarC
                            ASSOCIATES_DaG
                            ASSOCIATES_GaS
                            BINDS_CbP
                            BINDS_CbPD
                            CATALYZES_ECcR
                            CAUSES_CcSE
                            CAUSES_OcD
                            CLEAVESTO_PctP
                            CONSUMES_RcC
                            CONTAINS_CcG
                            CONTAINS_FcC
                            CONTRAINDICATES_CcD
                            DECREASEDIN_PdD
                            DOWNREGULATES_AdG
                            DOWNREGULATES_CdG
                            DOWNREGULATES_GPdG
                            DOWNREGULATES_KGdG
                            DOWNREGULATES_OGdG
                            ENCODES_GeM
                            ENCODES_GeP
                            EXPRESSEDIN_GeiCT
                            EXPRESSEDIN_GeiD
                            EXPRESSEDIN_PeCT
                            EXPRESSES_AeG
                            HAS_PhEC
                            INCLUDES_OiPW
                            INCLUDES_PCiC
                            INCREASEDIN_PiD
                            INTERACTS_PDiPD
                            INTERACTS_PiC
                            INTERACTS_PiP
                            ISA_AiA
                            ISA_CTiCT
                            ISA_DiD
                            ISA_ECiEC
                            ISA_FiF
                            ISA_OiO
                            ISA_PWiPW
                            LOCALIZES_DlA
                            MARKER_NEG_GmnD
                            MARKER_POS_GmpD
                            MEMBEROF_PDmPF
                            PARTICIPATES_CpR
                            PARTICIPATES_GpBP
                            PARTICIPATES_GpCC
                            PARTICIPATES_GpMF
                            PARTICIPATES_GpPW
                            PARTICIPATES_GpR
                            PARTICIPATES_PpR
                            PARTOF_ApA
                            PARTOF_CTpA
                            PARTOF_PDpP
                            PARTOF_PpC
                            PARTOF_RpPW
                            PRESENTS_DpS
                            PRODUCES_RpC
                            REDUCES_SEN_mGrsC
                            RESEMBLES_DrD
                            RESISTANT_TO_mGrC
                            RESPONSE_TO_mGrC
                            TARGETS_MtG
                            TRANSPORTS_PtC
                            TREATS_CtD
                            UPREGULATES_AuG
                            UPREGULATES_CuG
                            UPREGULATES_GPuG
                            UPREGULATES_KGuG
                            UPREGULATES_OGuG
                            """

few_shot = """<Example Question 1>Question 1: What are the known targets of the drug Metformin, and what diseases are these targets most commonly associated with? </Example Question 1>
              <Example Answer 1>AQL Statement 1: WITH Nodes, Edges
                                FOR compound IN Nodes
                                    FILTER 'Compound' IN compound.labels
                                    AND (
                                        compound.properties.identifier LIKE '%Metformin%'
                                        OR compound.properties.name LIKE '%Metformin%'
                                        OR compound.properties.synonyms LIKE '%Metformin%'
                                    )
                                    FOR edge IN Edges
                                        FILTER edge._from == compound._id
                                        FOR relatedNode IN Nodes
                                            FILTER relatedNode._id == edge._to
                                            RETURN {
                                                metformin: {
                                                    identifier: compound.properties.identifier,
                                                    name: compound.properties.name,
                                                    chembl_id: compound.properties.chembl_id
                                                },
                                                related: {
                                                    identifier: relatedNode.properties.identifier,
                                                    name: relatedNode.properties.name,
                                                    chembl_id: relatedNode.properties.chembl_id,
                                                    // Include any other fields you need from relatedNode
                                                },
                                                edgeLabel: edge.label
                                            }</Example Answer 1>
                
                <Example Question 2>Question 2: Which genes are most strongly associated with the development of Type 2 Diabetes, and what pathways do they influence?</Example Question 2>
                <Example Answer 2>AQL Statement 2: WITH Nodes, Edges
                                LET type2DiabetesGenes = (
                                    FOR disease IN Nodes
                                        FILTER 'Disease' IN disease.labels
                                        AND (
                                            (CONTAINS(LOWER(disease.properties.name), 'type 2') AND CONTAINS(LOWER(disease.properties.name), 'diabetes'))
                                            OR 
                                            (CONTAINS(LOWER(disease.properties.synonyms), 'type 2') AND CONTAINS(LOWER(disease.properties.synonyms), 'diabetes'))
                                        )
                                        FOR edge IN Edges
                                            FILTER edge._from == disease._id
                                            AND edge.label == 'ASSOCIATES_DaG'
                                            FOR geneNode IN Nodes
                                                FILTER geneNode._id == edge._to
                                                AND 'Gene' IN geneNode.labels
                                                COLLECT geneId = geneNode._id INTO genes
                                                RETURN geneId
                                )
                                FOR geneId IN type2DiabetesGenes
                                    FOR pathwayEdge IN Edges
                                        FILTER pathwayEdge._from == geneId
                                        AND pathwayEdge.label == 'PARTICIPATES_GpPW' // Assuming this label connects genes to pathways
                                        FOR pathwayNode IN Nodes
                                            FILTER pathwayNode._id == pathwayEdge._to
                                            AND 'Pathway' IN pathwayNode.labels
                                            RETURN {
                                                geneId: geneId,
                                                pathway: {
                                                    identifier: pathwayNode.properties.identifier,
                                                    name: pathwayNode.properties.name
                                                    // Add other properties you need
                                                }
                                            }</Example Answer 2>
"""

base_prompt = f"""
    <System Instructions>Answer the above question using the following data model and AQL query template.</System Instructions>
    
    <Graph Description>{graph_info}</Graph Description>

    <Edge Label Description>This is a list of the available edge labels in the graph. You can use these to filter edges in your AQL query.</Edge Label Description>
    <Available Edge Labels>{available_edge_labels}</Available Edge Labels>
    
    <Example Few-Shot Description>These questions and AQL queries demonstrate how to construct working AQL queries based on natural language questions using the provided node, edge, and edge label information. To adapt this query for different scenarios, modify the entity types, filter conditions, and return statements based on your specific data and question.</Example Few-Shot Description>
    <Example Few-Shot>{few_shot}</Example Few-Shot>
"""
