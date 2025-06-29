# test_email_assistant.py
from get_messages import get_unread_emails
from email_triage import triage_router
from config import sample_email
from memory_manager import EmailMemoryManager

def test_email_assistant():
    """Test the complete email assistant with different types of emails"""
    
    # Test with the sample email from the lesson (should be classified as "respond")
    print("\n=== TESTING SAMPLE EMAIL ===")
    result = triage_router(sample_email, memory)
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}\n")
    
    # Test with a marketing email (should be classified as "ignore")
    marketing_email = {
        "id": "test123",
        "sender": "Marketing Team <marketing@amazingdeals.com>",
        "recipient": "John Doe <john.doe@company.com>",
        "subject": "EXCLUSIVE OFFER: Limited Time Discount on Developer Tools!",
        "body": """Dear Valued Developer,
Don't miss out on this INCREDIBLE opportunity!
For a LIMITED TIME ONLY, get 80% OFF on our Premium Developer Suite!
FEATURES:
- Revolutionary AI-powered code completion
- Cloud-based development environment
- 24/7 customer support
- And much more!

Regular Price: $999/month
YOUR SPECIAL PRICE: Just $199/month!

Hurry! This offer expires in:
24 HOURS ONLY!

Click here to claim your discount: https://amazingdeals.com/special-offer
Best regards,
Marketing Team
---
To unsubscribe, click here
"""
    }
    
    print("\n=== TESTING MARKETING EMAIL ===")
    result = triage_router(marketing_email)
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}\n")
    
    # Test with a notification (should be classified as "notify")
    notification_email = {
        "id": "test234",
        "sender": "Build System <ci@company.com>",
        "recipient": "John Doe <john.doe@company.com>",
        "subject": "Build Complete: Project XYZ - Build #1234",
        "body": """Build Notification

Project: XYZ
Build: #1234
Status: SUCCESS

All tests passed. The artifacts are available at:
https://artifacts.company.com/xyz/1234

This is an automated message. Please do not reply.
"""
    }
    
    print("\n=== TESTING NOTIFICATION EMAIL ===")
    result = triage_router(notification_email, memory)
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}\n")
    
    # Test with a meeting request (should be classified as "respond")
    meeting_email = {
        "id": "test345",
        "sender": "Bob Johnson <bob.johnson@company.com>",
        "recipient": "John Doe <john.doe@company.com>",
        "subject": "Meeting to discuss project timeline",
        "body": """Hi John,

I'd like to schedule a meeting to discuss the project timeline for the auth service. 
Could we meet sometime next week to go over the milestones and deliverables?

Let me know what days work for you.

Thanks,
Bob
"""
    }
    
    print("\n=== TESTING MEETING REQUEST EMAIL ===")
    result = triage_router(meeting_email)
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}\n")

# Run the test
if __name__ == "__main__":
    # Initialize memory manager
    memory = EmailMemoryManager("test_email_memory.db")
    # test_email_assistant()

    

    
    
    unread_emails = get_unread_emails()
    result = triage_router(unread_emails[-1], memory)
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}\n")

    