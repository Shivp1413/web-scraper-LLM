# main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from typing import Optional
import uvicorn
from llama_cpp import Llama

# Initialize FastAPI
app = FastAPI(
    title="Web Scraper with Llama Content Extraction",
    description="Scrapes web content and uses Llama 3.1 to extract the meaningful content from HTML",
    version="1.0.0"
)

# Path to your Llama 3.1 model
# You'll need to download the GGUF version of Llama 3.1
MODEL_PATH = "models/llama-3.1-8b-instruct.Q4_K_M.gguf"  # Update with your model path

# Initialize Llama model
try:
    llama = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,  # Context window size
        n_gpu_layers=-1  # Use GPU acceleration if available
    )
    print("Llama model loaded successfully")
except Exception as e:
    print(f"Error loading Llama model: {e}")
    print("Will initialize model when first API call is made")
    llama = None

class WebsiteRequest(BaseModel):
    url: HttpUrl
    extract_mode: Optional[str] = "content"  # Options: "content", "summary", "info"

class ScrapedContent(BaseModel):
    url: str
    raw_html: str
    extracted_content: str
    status: str

@app.get("/")
def read_root():
    return {"message": "Web Scraper API with Llama 3.1 Content Extraction"}

@app.post("/scrape", response_model=ScrapedContent)
async def scrape_website(request: WebsiteRequest):
    global llama
    
    # Initialize model if not already done
    if llama is None:
        try:
            llama = Llama(
                model_path=MODEL_PATH,
                n_ctx=4096,
                n_gpu_layers=-1
            )
            print("Llama model loaded successfully on first API call")
        except Exception as e:
            raise HTTPException(status_code=500, 
                                detail=f"Failed to initialize Llama model: {str(e)}")
    
    # Fetch the website content
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(str(request.url), headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    
    html_content = response.text
    
    # Parse with BeautifulSoup to clean up
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "meta", "svg", "path"]):
        script.extract()
    
    # Get the clean HTML
    clean_html = str(soup)
    
    # Prepare prompt for Llama based on extract mode
    if request.extract_mode == "content":
        prompt = f"""
<instruction>
Extract the main textual content from this HTML. Ignore navigation menus, ads, footers, and other irrelevant content. Return only the main article content, properly formatted. 
</instruction>

<html>
{clean_html[:10000]}  # Limit input size to avoid context window issues
</html>
"""
    elif request.extract_mode == "summary":
        prompt = f"""
<instruction>
Summarize the main content of this webpage in 3-5 paragraphs. Focus on the core information presented.
</instruction>

<html>
{clean_html[:10000]}
</html>
"""
    elif request.extract_mode == "info":
        prompt = f"""
<instruction>
Extract key information from this webpage, including:
- Title
- Main topics covered
- Key points
- Any important data or statistics
- Author information (if available)
</instruction>

<html>
{clean_html[:10000]}
</html>
"""
    
    # Generate content with Llama
    try:
        llama_response = llama(
            prompt,
            max_tokens=2048,
            temperature=0.1,
            stop=["</answer>", "<instruction>"],
            echo=False
        )
        extracted_content = llama_response["choices"][0]["text"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, 
                            detail=f"Error generating content with Llama: {str(e)}")
    
    return ScrapedContent(
        url=str(request.url),
        raw_html=html_content[:1000] + "..." if len(html_content) > 1000 else html_content,  # Truncate for response
        extracted_content=extracted_content,
        status="success"
    )

@app.get("/models")
def get_model_info():
    return {
        "model_name": "Llama 3.1",
        "model_path": MODEL_PATH,
        "status": "loaded" if llama is not None else "not_loaded"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
