from neo4j import GraphDatabase
import pandas as pd
URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")

driver = GraphDatabase.driver(URI, auth=AUTH)

data_df = pd.read_csv("./data/Data.csv")
doi_df = pd.read_csv("./data/DOI.csv")
fusion_df = pd.read_csv("./data/Fusion Method.csv")


data_df.columns = data_df.columns.str.strip()
doi_df.columns = doi_df.columns.str.strip()
fusion_df.columns = fusion_df.columns.str.strip()

def import_data(tx, doi_df, fusion_df, data_df):

    # 1. Create Paper nodes
    for _, row in doi_df.iterrows():
        tx.run("""
            MERGE (p:Paper {doi: $doi})
            SET p.title = $title,
                p.authors = $authors,
                p.publication = $publication,
                p.year = $year,
                p.url = $url,
                p.keywords= $keywords,
                p.abstract = $abstract,
                p.publisher = $publisher,
                p.field = $field,
                p.isFusionPaper = $isFusionPaper,
                p.reason = $reason
        """, doi=row["DOI"], title=row["Title"], authors=row["Author"],
             publication=row["Publication Title"], year=row["PublicationDate"],
             url=row["URL"], keywords=row["Keywords"], abstract=row["Abstract"], publisher=row["Publisher"], field=row["Field of Study"], isFusionPaper=row["IsDataFusionPaper"], reason=row["DataFusionClassificationReason"])

    # 2. Create FusionMethod nodes
    for _, row in fusion_df.iterrows():
        tx.run("""
            MERGE (m:FusionMethod {key: $key})
            SET m.name = $name,
                m.key = $key,
                m.doi = $doi,
                m.description = $description,
                m.u1 = $u1,
                m.u3 = $u3,
                m.output = $output
        """, key=row["Method Key"], name=row["Method Name"], doi=row["DOI"],
             description=row["Description"], u1=row["U1"], u3=row["U3"], output=row["Output Data"])

    # 3. Create Dataset nodes
    for _, row in data_df.iterrows():
        tx.run("""
            MERGE (d:Dataset {name: $name})
            SET d.doi = $doi,
                d.name = $name,
                d.url = $url,
                d.key = $key,
                d.dataType = $dataType,
                d.collectionMethod = $collectionMethod,
                d.u2 = $u2,
                d.spatialCoverage = $spatialCoverage,
                d.temporalCoverage = $temporalCoverage,
                d.format = $format,
                d.license = $license,
                d.provenance = $provenance
        """, name=row["Data Name"], doi=row["DOI"], url=row["DatasetURL"], key=row["Method Key"],
             dataType=row["Data Type"], collectionMethod=row["Collection Method"], u2=row["U2"],
             spatialCoverage=row["SpatialCoverage"], temporalCoverage=row["TemporalCoverage"],
             format=row["Format"], license=row["License"], provenance=row["Provenance"])

    # 4. Paper -[:USES_METHOD]-> FusionMethod
    for _, row in fusion_df.iterrows():
        tx.run("""
            MATCH (p:Paper {doi: $doi})
            MATCH (m:FusionMethod {key: $key})
            MERGE (p)-[:USES_METHOD]->(m)
        """, doi=row["DOI"], key=row["Method Key"])

    # 5. Paper -[:USES_DATASET]-> Dataset
    for _, row in data_df.iterrows():
        tx.run("""
            MATCH (p:Paper {doi: $doi})
            MATCH (d:Dataset {name: $name, doi: $doi})
            MERGE (p)-[:USES_DATASET]->(d)
        """, doi=row["DOI"], name=row["Data Name"])

    # 6. FusionMethod -[:APPLIED_TO]-> Dataset
    for _, row in data_df.iterrows():
        tx.run("""
            MATCH (m:FusionMethod {key: $key})
            MATCH (d:Dataset {name: $name})
            MERGE (m)-[:APPLIED_TO]->(d)
        """, key=row["Method Key"], name=row["Data Name"])

with driver.session() as session:
    session.execute_write(import_data, doi_df, fusion_df, data_df)
    print("Import complete!")

driver.close()
