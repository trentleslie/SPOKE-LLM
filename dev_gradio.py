import gradio as gr
import requests
import traceback
import logging
from api_key import auth, url

# Configure logging
logging.basicConfig(filename='error.log', level=logging.ERROR)

def ask(text):
    try:
        prompt = {
            "model": "gemini-pro",
            "messages": [{"role": "user", "content": text}]
        }
        headers = {
            "Authorization": auth,
            "Content-Type": "application/json"
        }
        url = url
        response = requests.post(url, headers=headers, json=prompt)
        
        # Log status code and raw response content
        status_code = response.status_code
        response_content = response.text
        
        # Check if the request was successful
        if status_code != 200:
            error_message = f"Error: Received status code {status_code}\nResponse content: {response_content}"
            logging.error(error_message)
            return error_message
        
        # Log the raw JSON response for debugging
        result = response.json()
        logging.info(f"Raw JSON response: {result}")
        
        # Access the correct part of the response
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0].get('message', {}).get('content', 'No content found')
            logging.info(f"Extracted content: {content}")
            return content
        else:
            error_message = "Error: Unexpected response structure"
            logging.error(error_message)
            return error_message
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        return f"Request error: {str(e)}"
    except Exception as e:
        logging.error(f"Error: {str(e)}\n\n{traceback.format_exc()}")
        return f"Error: {str(e)}\n\n{traceback.format_exc()}"

with gr.Blocks() as server:
    with gr.Tab("LLM Inferencing"):
        model_input = gr.Textbox(label="Your Question:", 
                                 value="What’s your question?", interactive=True)
        ask_button = gr.Button("Ask")
        model_output = gr.Textbox(label="The Answer:", interactive=False, 
                                  value="Answer goes here...")

        ask_button.click(ask, inputs=[model_input], outputs=[model_output])

server.launch(share=True)
