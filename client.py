# client.py
import requests
import argparse
import json

def scrape_url(url, mode="content"):
    """
    Call the local scraper API to extract content from a URL
    
    Args:
        url (str): The URL to scrape
        mode (str): Extract mode - "content", "summary", or "info"
        
    Returns:
        dict: The API response
    """
    api_endpoint = "http://localhost:8000/scrape"
    
    payload = {
        "url": url,
        "extract_mode": mode
    }
    
    try:
        response = requests.post(api_endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for Web Scraper API")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--mode", choices=["content", "summary", "info"], 
                        default="content", help="Content extraction mode")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    print(f"Scraping {args.url} with mode: {args.mode}")
    result = scrape_url(args.url, args.mode)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("\n--- EXTRACTED CONTENT ---\n")
        print(result["extracted_content"])
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"\nFull result saved to {args.output}")
