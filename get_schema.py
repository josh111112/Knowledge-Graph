from neo4j import GraphDatabase
URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")

driver = GraphDatabase.driver(URI, auth=AUTH)

def get_schema(driver):
    with driver.session() as session:
        nodes = session.run("CALL db.schema.nodeTypeProperties()").data()
        rels = session.run("""
            MATCH (a)-[r]->(b)
            RETURN DISTINCT labels(a)[0] AS startLabel, type(r) AS relType, labels(b)[0] AS endLabel
        """).data()

    # Group properties by label
    label_props = {}
    for row in nodes:
        label = row["nodeType"].strip(":`")
        prop = row["propertyName"]
        if label not in label_props:
            label_props[label] = []
        if prop:
            label_props[label].append(prop)

    schema = "Node labels and properties:\n"
    for label, props in label_props.items():
        schema += f"- {label}: {', '.join(props)}\n"

    schema += "\nRelationships:\n"
    seen = set()
    for row in rels:
        rel = f"({row['startLabel']})-[:{row['relType']}]->({row['endLabel']})"
        if rel not in seen:
            schema += f"- {rel}\n"
            seen.add(rel)

    return schema
driver.close()