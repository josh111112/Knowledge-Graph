from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from neo4j import GraphDatabase
from get_schema import get_schema
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.llm import OpenAILLM
import os
from openai import OpenAI
from dotenv import load_dotenv

import logging

load_dotenv()

# debugging
logging.getLogger("neo4j_graphrag").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = Flask(__name__)
CORS(app)

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
- MUST BE A SINGLE VALID CYPHER QUERY. If you need to combine multiple MATCHes that don't depend on each other, use UNION or combine them into a single RETURN.

Examples:
{examples}

Generate a Cypher query for this question:
{query_text}

Return only the Cypher query, no explanation, no markdown backticks, no newlines.
"""
formatted_examples = "\n".join(
    [f"Q: {e['question']}\nCypher: {e['cypher']}" for e in examples]
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

llm = OpenAILLM(
    model_name="gemini-3.1-pro-preview",
    base_url=GEMINI_BASE_URL,
    api_key=GEMINI_API_KEY,
)

gemini_client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GEMINI_BASE_URL,
)

retriever = Text2CypherRetriever(
    driver=driver,
    llm=llm,
    neo4j_schema=GRAPH_SCHEMA,
    custom_prompt=CUSTOM_PROMPT,
    examples=[formatted_examples]
)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    query_text = data.get('query')
    if not query_text:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # Step 1: Intent Classification
        intent_sys_msg = """You are a router for a research knowledge graph about data fusion papers.
Determine if the user's input is a general conversational message (e.g., "hello", "who are you") OR if it is a specific query that requires searching a database for research papers, datasets, methods, or uncertainties (e.g., "show me papers", "what is u2").
Reply with EXACTLY ONE WORD: either "GENERAL" or "DATABASE"."""
        
        intent_res = gemini_client.chat.completions.create(
            model="gemini-3.1-pro-preview",
            messages=[
                {"role": "system", "content": intent_sys_msg},
                {"role": "user", "content": query_text}
            ]
        )
        intent = intent_res.choices[0].message.content.strip().upper()

        if "GENERAL" in intent:
            # It's a general question, respond immediately without querying Neo4j
            chat_res = gemini_client.chat.completions.create(
                model="gemini-3.1-pro-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful and friendly assistant for a research knowledge graph about data fusion papers. Keep your answer brief and conversational."},
                    {"role": "user", "content": query_text}
                ]
            )
            return jsonify({
                "responses": [],
                "summary": chat_res.choices[0].message.content
            })

        # Step 2: Proceed with Database Query as normal if intent is DATABASE
        result = retriever.search(query_text=query_text)
        
        responses = []
        for item in result.items:
            text = item.content
            # Clean up the "<Record key='value'>" string format
            if text.startswith("<Record ") and text.endswith(">"):
                text = text[8:-1] # Remove "<Record " and ">"
            responses.append(text)
            
        summary = ""
        if responses:
            prompt_context = "\n".join(responses)
            sys_msg = "You are a helpful research assistant. Use the provided database records to answer the user's question in a clear, conversational, and concise way."
            user_msg = f"Database Records:\n{prompt_context}\n\nUser Question: {query_text}"
            
            try:
                chat_res = gemini_client.chat.completions.create(
                    model="gemini-3.1-pro-preview",
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg}
                    ]
                )
                summary = chat_res.choices[0].message.content
            except Exception as e:
                summary = "I found the results, but I encountered an error while trying to summarize them: " + str(e)
            
        return jsonify({
            "responses": responses,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)
