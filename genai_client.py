import os
from dotenv import load_dotenv
from google import genai


def initialize_genai_client():
    """Initialize and return a Gemini client"""
    # Load environment variables
    _ = load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    # print(api_key)

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found")
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    return client


def generate_content(prompt, model_name="gemini-2.0-flash"):
    client = initialize_genai_client()
    """Generate content using the Gemini model"""
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return response.text



if __name__ == '__main__':
    # Create client instance
    prompt = input("Enter your content: ")
    print(generate_content(prompt))