from neo4j import GraphDatabase
from get_schema import get_schema
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.llm import OllamaLLM
import os
from dotenv import load_dotenv
import logging

load_dotenv()

URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))
driver = GraphDatabase.driver(URI, auth=AUTH)

GRAPH_SCHEMA = get_schema(driver)

examples = [
    {
        "question": "Show me all fusion methods used for Traffic Data.",
        "cypher": """MATCH (m:FusionMethod)-[:APPLIED_TO]->(d:Dataset)
WHERE d.dataType CONTAINS 'Traffic'
RETURN DISTINCT m.name AS methodName, m.description AS methodDescription"""
    },
    {
        "question": "List all papers that report U2 (Measurement) uncertainty for Satellite Imagery.",
        "cypher": """MATCH (p:Paper)-[:USES_DATASET]->(d:Dataset)
WHERE d.dataType CONTAINS 'Satellite' AND d.u2 IS NOT NULL
RETURN DISTINCT p.title AS paperTitle, p.doi AS doi, d.u2 AS measurementUncertainty"""
    },
    {
        "question": "Which datasets are commonly fused with Census Data?",
        "cypher": """MATCH (m:FusionMethod)-[:APPLIED_TO]->(d1:Dataset)
MATCH (m)-[:APPLIED_TO]->(d2:Dataset)
WHERE d1.name CONTAINS 'Census' AND d1.name <> d2.name
RETURN DISTINCT d2.name AS coFusedDataset, d2.dataType AS dataType"""
    }
]

CUSTOM_PROMPT = """
You are an expert Neo4j Cypher query generator for a research knowledge graph about data fusion papers.
DO NOT INCLUDE NEWLINE CHARACTERS IN YOUR RESPONSE.
Given the following graph schema:
{schema}

Rules you must follow:
- Only use node labels, relationship types, and properties that exist in the schema above
- Always use CONTAINS for text matching, never exact string equality for descriptive fields
- Always use DISTINCT to avoid duplicate results
- Return meaningful property names as aliases (e.g. AS paperTitle, AS methodName)
- Never return node objects directly, always return specific properties
- If asked about uncertainties, u1 = method assumptions, u2 = dataset limitations, u3 = method evaluation limitations

Examples:
{examples}

Generate a Cypher query for this question:
{query_text}

Return only the Cypher query, no explanation, no markdown backticks, no newlines.
"""
formatted_examples = "\n".join(
    [f"Q: {e['question']}\nCypher: {e['cypher']}" for e in examples]
)

llm = OllamaLLM(model_name="gemma3:12b")

# debugging
logging.getLogger("neo4j_graphrag").setLevel(logging.DEBUG)
logging.basicConfig(format="%(message)s")

retriever = Text2CypherRetriever(
    driver=driver,
    llm=llm,
    neo4j_schema=GRAPH_SCHEMA,
    custom_prompt=CUSTOM_PROMPT,
    examples=[formatted_examples]
)

query_text = "List all papers that report U2 (Measurement) uncertainty for LiDAR."

print(f"\nQuestion: {query_text}")
result = retriever.search(query_text=query_text)
print("Generated Cypher:")
print(result.metadata["cypher"])
print("Results:")
for item in result.items:
    print(" -", item.content)

driver.close()