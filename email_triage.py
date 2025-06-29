"""
The triage system's job is to classify incoming emails into three categories:

Respond: Emails requiring a reply
Ignore: Emails you can safely skip
Notify: Important information that doesn't need a response

"""
import datetime
from typing import Literal, Dict, Any, Tuple

# from user_profile import profile, prompt_instructions, sample_email
from genai_client import generate_content
from memory_manager import EmailMemoryManager, EmailRecord

from config import (
    profile,
    prompt_instructions,
    triage_system_prompt, 
    triage_user_prompt, 
    response_format_instruction, 
    agent_system_prompt,
    agent_user_prompt
)


class Router:
    """
    Analyze an unread email and route it according to its content.
    """
    def __init__(self, reasoning: str, classification: Literal["ignore", "respond", "notify"]):
        self.reasoning = reasoning
        self.classification = classification

def classify_email(email_data: Dict[str, str], memory: EmailMemoryManager) -> Router:
    """
    Classify an email using the Gemini model
    
    Args:
        email_data: Dictionary containing email details
                   (from, to, subject, body)
        memory: The memory manager in charge of data storage and retrieval
    
    Returns:
        Router object with classification and reasoning
    """
    # Get author history for context
    author_history = memory.format_author_history_for_prompt(email_data['sender'])

    # Format the system prompt with profile and rules
    system_prompt = triage_system_prompt.format(
        full_name=profile["full_name"],
        name=profile["name"],
        user_profile_background=profile["user_profile_background"],
        triage_ignore=prompt_instructions["triage_rules"]["ignore"],
        triage_notify=prompt_instructions["triage_rules"]["notify"],
        triage_respond=prompt_instructions["triage_rules"]["respond"],
        examples=f"Previous interactions with this sender:\n{author_history}" 
    )
    
    # Format the user prompt with email details
    user_prompt = triage_user_prompt.format(
        author=email_data["sender"],
        to=email_data["recipient"],
        subject=email_data["subject"],
        email_thread=email_data["body"]
    )
    
    # Combine prompts for Gemini
    combined_prompt = system_prompt + "\n\n" + user_prompt + "\n\n" + response_format_instruction
    
    # Call Gemini model
    result_text = generate_content(combined_prompt)
    
    # Parse the classification and reasoning
    classification, reasoning = extract_classification(result_text)
    
    return Router(
        reasoning=reasoning,
        classification=classification
    )
    

def extract_classification(result_text: str) -> Tuple[Literal["ignore", "respond", "notify"], str]:
    """
    Extract structured classification and reasoning from the LLM response
    
    Args:
        result_text: The text response from the LLM
        
    Returns:
        Tuple of (classification, reasoning)
    """
    lines = result_text.strip().split('\n')
    classification = "respond"  # Default
    reasoning = result_text  # Default to the full text
    
    # Extract the classification
    for line in lines:
        if line.upper().startswith("CLASSIFICATION:"):
            classification_text = line.upper().replace("CLASSIFICATION:", "").strip()
            if "IGNORE" in classification_text:
                classification = "ignore"
            elif "NOTIFY" in classification_text:
                classification = "notify"
            elif "RESPOND" in classification_text:
                classification = "respond"
            break
    
    # Try to extract reasoning if formatted as requested
    reasoning_section = False
    reasoning_lines = []
    
    for line in lines:
        if line.upper().startswith("REASONING:"):
            reasoning_section = True
            continue
        
        if reasoning_section:
            reasoning_lines.append(line)
    
    if reasoning_lines:
        reasoning = "\n".join(reasoning_lines)
    
    return classification, reasoning



def triage_router(email_data: Dict[str, str], memory: EmailMemoryManager) -> Dict[str, Any]:
    """
    Analyze an email and determine the next action
    
    Args:
        email_data: Dictionary with email details
        memory: The email memory manger in charge of data storage and retrival
        
    Returns:
        Dictionary with action information
    """
    
    # Classify the email
    result = classify_email(email_data, memory)
    
    # Store the decision in memory
    email_record = EmailRecord(
        email_id=email_data["id"],
        author=email_data["sender"],
        subject=email_data["subject"],
        classification=result.classification,
        reasoning=result.reasoning,
        thread_summary="", # TODO: Add summarization logic
        timestamp=datetime.datetime.now(),
        raw_content=email_data["body"]
    )
    memory.store_email_decision(email_record)

    # Take appropriate action based on classification
    if result.classification == "ignore":
        print(f"Classification: IGNORE - This email can be safely ignored")
        return {
            "action": "ignore",
            "reason": result.reasoning
        }
    
    elif result.classification == "notify":
        print(f"Classification: NOTIFY - This email contains important information")
        return {
            "action": "notify",
            "email": email_data,
            "reason": result.reasoning
        }
    
    elif result.classification == "respond":
        print(f"Classification: RESPOND - This email requires a response")
        
        # TODO: design a function to reply message
        reply_message = ""
        return {
            "action": "respond",
            "email": email_data,
            "reason": result.reasoning,
            "response": reply_message
        }
  

if __name__ == "__main__":
    pass
        

