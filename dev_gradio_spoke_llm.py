import os
import json
import io
import sys
import re
import logging
import traceback
from contextlib import redirect_stdout
from typing import Dict, List, Any
from arango import ArangoClient
from langchain_community.graphs import ArangoGraph  # Updated import
from langchain_openai import ChatOpenAI
from langchain.chains import ArangoGraphQAChain
from api_key import openai_api_key
from prompts_openai import base_prompt
import gradio as gr

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = openai_api_key

# Configure logging
logging.basicConfig(filename='error.log', level=logging.ERROR)

# Initialize ChatOpenAI
try:
    llm = ChatOpenAI(temperature=0, model='gpt-4o')
    print("Initialization successful!")
except Exception as e:
    print(f"Initialization failed: {e}")

# Initialize the ArangoDB client and connect to the database
client = ArangoClient(hosts='http://127.0.0.1:8529')
db = client.db('spoke23_human', username='root', password='ph')

# Fetch the existing graph from the database
graph = ArangoGraph(db)

# Instantiate ArangoGraphQAChain
qa_chain = ArangoGraphQAChain.from_llm(llm, graph=graph, verbose=True, return_aql_query=True, return_aql_result=True)

def capture_stdout(func, *args, **kwargs) -> str:
    f = io.StringIO()
    with redirect_stdout(f):
        func(*args, **kwargs)
    captured_output = f.getvalue()
    return captured_output

def execute_aql(query: str, qa_chain) -> Dict[str, str]:
    captured_output = capture_stdout(qa_chain.invoke, {qa_chain.input_key: query})
    return {'captured_output': captured_output}

def clean_output(output: str) -> str:
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    cleaned_output = ansi_escape.sub('', output)
    return cleaned_output

def fix_json_format(aql_result_line: str) -> str:
    fixed_json = aql_result_line.replace("'", '"').replace('\\', '\\\\').replace('\n', '\\n')
    return fixed_json

def extract_aql_result(captured_output: str) -> Dict[str, list]:
    cleaned_output = clean_output(captured_output)
    lines = cleaned_output.splitlines()
    aql_result_line = None
    for i, line in enumerate(lines):
        if "AQL Result:" in line:
            if i + 1 < len(lines):
                aql_result_line = lines[i + 1].strip()
            break

    if aql_result_line:
        try:
            fixed_json = fix_json_format(aql_result_line)
            aql_result = json.loads(fixed_json)
            return {'aql_result': aql_result}
        except json.JSONDecodeError:
            pass
    return {'aql_result': []}

def interpret_aql_result(aql_result: List[Dict[str, Any]], llm, user_question=None) -> str:
    prompt = (
        f'''Based on the following AQL results, provide a detailed and comprehensive scientific interpretation answering the question: "{user_question}" based on the following template.
        
        Introduction:
            Context: Start with the broader context of your research.
                Example: "In the study of hereditary breast cancer, the BRCA1 gene plays a crucial role."
        Entity Description:
            Gene Description:
                ID: Reference the unique identifier.
                Label: Use the human-readable name.
                Example: "The gene BRCA1 (ID: genes/12345) is known for its involvement in DNA repair mechanisms."
        Relationships:
            Associations:
                Describe the relationships and use both IDs and labels.
                Example: "BRCA1 (ID: genes/12345) has been found to be associated with several diseases. Notably, it shows a strong association with breast cancer (ID: diseases/67890). This association (type: 'gene-disease') is crucial for understanding the genetic basis of the disease."
        Detailed Explanation:
            Exploring the Data:
                Dive deeper into the data and explain the significance.
                Example: "The association between BRCA1 and breast cancer (ID: diseases/67890) highlights the gene's role in tumor suppression. Mutations in BRCA1 can lead to a loss of function, contributing to the development of cancer."
        Conclusion:
            Summary and Implications:
                Summarize the key points and discuss the implications.
                Example: "Understanding the relationship between BRCA1 (ID: genes/12345) and breast cancer (ID: diseases/67890) is vital for developing targeted therapies. The genetic insights provided by this association can guide personalized treatment approaches.
                
        AQL Results: {aql_result}'''
    )
    response = llm.invoke(prompt)
    return response.content

def sequential_chain(query: str, qa_chain, user_question=None) -> Dict[str, Any]:
    response = execute_aql(query, qa_chain)
    captured_output = response['captured_output']
    final_response = extract_aql_result(captured_output)
    
    aql_result = final_response.get('aql_result', [])
    if aql_result:
        scientific_story = interpret_aql_result(aql_result, llm, user_question)
        final_response['scientific_story'] = scientific_story

    return [captured_output, final_response]

def execute_query_with_retries(query: str, qa_chain, max_attempts=3, user_question=None):
    attempt = 1
    success = False
    failure_message = ("The prior AQL query failed to return results. "
                       "Please think this through step by step and refine your AQL statement. "
                       "The original question is as follows:")

    while attempt <= max_attempts and not success:
        print(f"Attempt {attempt}: Executing query...")
        response = sequential_chain(query, qa_chain, user_question)
        aql_query = response[0]
        aql_result = response[1].get('aql_result', [])

        if aql_result:
            success = True
            print(f"\nAttempt {attempt} - AQL Result:\n{aql_result}")
            print(f"LLM Interpretation:\n{response[1].get('scientific_story')}")
        else:
            print(f"\nAttempt {attempt} - AQL Result: No result found.")
            if attempt < max_attempts:
                query = f"{failure_message} {query}"
            else:
                print("No result found after", max_attempts, "tries.")

        attempt += 1
        
    return [attempt - 1, aql_query, aql_result, response[1].get('scientific_story')]

# Gradio app
def ask(text):
    try:
        question = text + base_prompt
        attempt_count, aql_query, aql_result, scientific_story = execute_query_with_retries(question, qa_chain, 10, text)
        return f'Attempt Count: {attempt_count}\n\nAQL Info: {aql_query}\n\nLLM Interpretation:\n{scientific_story}'
    except Exception as e:
        logging.error(f"Error: {str(e)}\n\n{traceback.format_exc()}")
        return f"Error: {str(e)}\n\n{traceback.format_exc()}"

with gr.Blocks() as server:
    with gr.Tab("LLM Inferencing"):
        model_input = gr.Textbox(label="Your Question:", value="What’s your question?", interactive=True)
        ask_button = gr.Button("Ask")
        model_output = gr.Markdown(label="The Answer:")

        ask_button.click(ask, inputs=[model_input], outputs=[model_output])
        
        # Custom JavaScript to trigger the ask button on Enter key press
        #server.load(_js="""
        #    function() {
        #        const textbox = document.querySelector('textarea');
        #        textbox.addEventListener('keypress', function(event) {
        #            if (event.key === 'Enter') {
        #                event.preventDefault();  // Prevent default action to avoid new line
        #                document.querySelector('button').click();
        #            }
        #        });
        #    }
        #""")

server.launch(share=True)
