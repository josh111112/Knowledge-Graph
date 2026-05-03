# Terra — Research Knowledge Graph 🌍

Terra is a GraphRAG-powered AI research assistant designed to help researchers explore data fusion methodologies, datasets, and paper uncertainties. By leveraging a Neo4j Knowledge Graph and Large Language Models (LLMs), Terra translates natural language questions into precise Cypher queries, retrieves relevant academic data, and provides synthesized, conversational answers.

## ✨ Features

- **Knowledge Graph Storage:** Models complex relationships between research `Papers`, `Datasets`, and `FusionMethods` using Neo4j.
- **Natural Language to Cypher (Text2Cypher):** Uses `neo4j-graphrag` to convert user questions into database queries.
- **Intent Routing:** Automatically detects whether a query is a general conversation or requires a database search.
- **Beautiful Web Interface:** A modern, responsive chat UI built with HTML and Tailwind CSS.
- **Flexible LLM Support:** Comes configured with Gemini via OpenAI's SDK in the web app, and includes an Ollama fallback for local CLI testing.

## 📁 Project Structure

- `app.py`: The main Flask web server. Handles routing, intent classification, and GraphRAG execution using the Gemini API.
- `index.html`: The frontend user interface for Terra AI.
- `import_data.py`: A data ingestion script that reads CSV files and populates the Neo4j graph database.
- `get_schema.py`: A utility script that dynamically extracts the nodes, properties, and relationships from the Neo4j database to feed into the LLM prompt.
- `main.py`: A CLI-based testing script that uses a local Ollama model (`gemma3:12b`) for Text-to-Cypher retrieval.
- `data/`: Directory containing the source CSV files:
  - `Data.csv`: Information about datasets, collection methods, and format limitations.
  - `DOI.csv`: Metadata for research papers (Title, Authors, Abstract, etc.).
  - `Fusion Method.csv`: Details on fusion methods, assumptions, limitations, and outputs.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Neo4j](https://neo4j.com/download/) (Desktop or AuraDB) running locally on the default port (`bolt://localhost:7687` or `neo4j://127.0.0.1:7687`)
- Gemini API Key

### Installation

1. **Install the required Python dependencies:**
