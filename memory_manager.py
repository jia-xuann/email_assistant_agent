'''
Handle storage and retrieval for emial processing decisions
'''

import sqlite3
import json
import datetime

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass # automatically generates common methods for the classes
class EmailRecord:
    email_id: str 
    author: str
    subject: str
    classification: str
    reasoning: str
    thread_summary: str
    timestamp: datetime.datetime
    response_sent: bool = False
    raw_content: str = ""

@dataclass
class ConversationPattern:
    author_domain: str                 # "@company.com"
    typical_classification: str        # ['Ignore', 'Notify', 'Response']
    keywords: List[str]                # ['newsletter', 'meeting',...]
    frequency: int                   
    last_seen: datetime.datetime

class EmailMemoryManager:
    """Manages persistent memory for email assistant decisions and context"""
    
    def __init__(self, db_path: str = "email_assistant.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with all memory tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Email processing history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_history (
                email_id TEXT PRIMARY KEY,
                author TEXT NOT NULL,
                subject TEXT,
                classification TEXT NOT NULL,
                reasoning TEXT,
                thread_summary TEXT,
                timestamp DATETIME NOT NULL,
                response_sent BOOLEAN DEFAULT FALSE,
                raw_content TEXT,
                UNIQUE(email_id)
            )
        """) # UNIQUE() -- prevent duplicate email records
        
        # User preferences and dynamic context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                updated_at DATETIME NOT NULL,
                UNIQUE(key)  
            )
        """) 
        
        # Learning patterns from email interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_domain TEXT NOT NULL,
                typical_classification TEXT NOT NULL,
                keywords TEXT, -- JSON array of keywords
                frequency INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.5,
                last_seen DATETIME NOT NULL
            )
        """)
        
        # Response templates and drafts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT UNIQUE NOT NULL,
                template_content TEXT NOT NULL,
                use_count INTEGER DEFAULT 0,
                category TEXT DEFAULT 'general',
                created_at DATETIME NOT NULL,
                last_used DATETIME
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_author ON email_history(author)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_timestamp ON email_history(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_classification ON email_history(classification)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_domain ON conversation_patterns(author_domain)")
        
        conn.commit()
        conn.close()
    
    # === EMAIL HISTORY OPERATIONS ===
    
    def store_email_decision(self, email_record: EmailRecord) -> bool:
        """Store email processing decision"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO email_history 
                (email_id, author, subject, classification, reasoning, 
                 thread_summary, timestamp, response_sent, raw_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_record.email_id,
                email_record.author,
                email_record.subject,
                email_record.classification,
                email_record.reasoning,
                email_record.thread_summary,
                email_record.timestamp,
                email_record.response_sent,
                email_record.raw_content
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            print(f"Database error storing email decision: {e}")
            return False
    
    def get_author_history(self, author: str, limit: int = 5) -> List[EmailRecord]:
        """Get recent email history with specific author"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT email_id, author, subject, classification, reasoning, 
                   thread_summary, timestamp, response_sent, raw_content
            FROM email_history 
            WHERE author = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (author, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [EmailRecord(
            email_id=r[0], author=r[1], subject=r[2], classification=r[3],
            reasoning=r[4], thread_summary=r[5], 
            timestamp=datetime.datetime.fromisoformat(r[6]),
            response_sent=bool(r[7]), raw_content=r[8]
        ) for r in results]
    
    def get_similar_subjects(self, subject: str, limit: int = 3) -> List[EmailRecord]:
        """Find emails with similar subjects for context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple similarity using LIKE - could be enhanced with fuzzy matching
        cursor.execute("""
            SELECT email_id, author, subject, classification, reasoning, 
                   thread_summary, timestamp, response_sent, raw_content
            FROM email_history 
            WHERE subject LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (f"%{subject}%", limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [EmailRecord(
            email_id=r[0], author=r[1], subject=r[2], classification=r[3],
            reasoning=r[4], thread_summary=r[5], 
            timestamp=datetime.datetime.fromisoformat(r[6]),
            response_sent=bool(r[7]), raw_content=r[8]
        ) for r in results]
    
    def mark_response_sent(self, email_id: str) -> bool:
        """Mark an email as having been responded to"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE email_history 
                SET response_sent = TRUE 
                WHERE email_id = ?
            """, (email_id,))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            print(f"Database error marking response: {e}")
            return False
    
    # === USER CONTEXT OPERATIONS ===
    
    def update_user_context(self, key: str, value: str, category: str = 'general') -> bool:
        """
        Update user context/preferences
        e.g.,

        # Learning user's preferences
        memory.update_user_context("preferred_meeting_time", "2pm-4pm", "scheduling")

        # Learning user's work patters
        memory.update_user_context("busy_days", "Monday, Wednesday", "workload")

        # Learning user's communication style
        memory.update_user_context("formal_contacts", "@legal.com, @board.com", "tone")

        
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_context (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
            """, (key, value, category, datetime.datetime.now()))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            print(f"Database error updating context: {e}")
            return False
    
    def get_user_context(self, key: str) -> Optional[str]:
        """Get user context value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM user_context WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_user_context_by_category(self, category: str) -> Dict[str, str]:
        """Get all user context for a category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM user_context WHERE category = ?", (category,))
        results = cursor.fetchall()
        conn.close()
        
        return {key: value for key, value in results}
    
    # === PATTERN LEARNING ===
    
    def update_conversation_pattern(self, author_domain: str, classification: str, 
                                  keywords: List[str]) -> bool:
        """Update or create conversation pattern for learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if pattern exists
            cursor.execute("""
                SELECT pattern_id, frequency FROM conversation_patterns 
                WHERE author_domain = ? AND typical_classification = ?
            """, (author_domain, classification))
            
            result = cursor.fetchone()
            
            if result:
                # Update existing pattern
                pattern_id, frequency = result
                cursor.execute("""
                    UPDATE conversation_patterns 
                    SET frequency = frequency + 1, 
                        keywords = ?,
                        last_seen = ?
                    WHERE pattern_id = ?
                """, (json.dumps(keywords), datetime.datetime.now(), pattern_id))
            else:
                # Create new pattern
                cursor.execute("""
                    INSERT INTO conversation_patterns 
                    (author_domain, typical_classification, keywords, frequency, last_seen)
                    VALUES (?, ?, ?, 1, ?)
                """, (author_domain, classification, json.dumps(keywords), datetime.datetime.now()))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            print(f"Database error updating pattern: {e}")
            return False
    
    def get_author_patterns(self, author_domain: str) -> List[ConversationPattern]:
        """Get learned patterns for an author domain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT author_domain, typical_classification, keywords, frequency, last_seen
            FROM conversation_patterns 
            WHERE author_domain = ?
            ORDER BY frequency DESC
        """, (author_domain,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [ConversationPattern(
            author_domain=r[0],
            typical_classification=r[1],
            keywords=json.loads(r[2]) if r[2] else [],
            frequency=r[3],
            last_seen=datetime.datetime.fromisoformat(r[4])
        ) for r in results]
    
    # === ANALYTICS AND REPORTING ===
    
    def get_daily_summary(self, date: datetime.date = None) -> Dict[str, int]:
        """Get summary of email processing for a specific date"""
        if date is None:
            date = datetime.date.today()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT classification, COUNT(*) 
            FROM email_history 
            WHERE DATE(timestamp) = ? 
            GROUP BY classification
        """, (date,))
        
        results = cursor.fetchall()
        conn.close()
        
        summary = {'IGNORE': 0, 'NOTIFY': 0, 'RESPOND': 0, 'total': 0}
        for classification, count in results:
            summary[classification] = count
            summary['total'] += count
        
        return summary
    
    def get_weekly_stats(self) -> Dict[str, any]:
        """Get weekly email processing statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        week_ago = datetime.date.today() - datetime.timedelta(days=7)
        
        cursor.execute("""
            SELECT 
                DATE(timestamp) as day,
                classification,
                COUNT(*) as count
            FROM email_history 
            WHERE DATE(timestamp) >= ?
            GROUP BY DATE(timestamp), classification
            ORDER BY day DESC
        """, (week_ago,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Organize by day
        stats = {}
        for day, classification, count in results:
            if day not in stats:
                stats[day] = {'IGNORE': 0, 'NOTIFY': 0, 'RESPOND': 0}
            stats[day][classification] = count
        
        return stats
    
    def get_top_senders(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequent email senders"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT author, COUNT(*) as email_count
            FROM email_history 
            GROUP BY author
            ORDER BY email_count DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    # === UTILITY METHODS ===
    
    def format_author_history_for_prompt(self, author: str, limit: int = 3) -> str:
        """Format author history for LLM prompt context"""

        # 1.1 Get raw database records
        history = self.get_author_history(author, limit)
        
        # 1.2 Handle empty case
        if not history:
            return "No previous interactions with this sender."
        
        # 2. Format each record into readable text
        # e.g., "- 2025-06-30: RESPOND - Meeting request for project discussion"
        formatted = []
        for record in history:
            date_str = record.timestamp.strftime("%Y-%m-%d")
            formatted.append(
                f"- {date_str}: {record.classification} - {record.thread_summary}"
            )

        
        return "\n".join(formatted)
    
    def extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        return email.split('@')[-1].lower() if '@' in email else email.lower()
    
    def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """Clean up old email records to prevent database bloat"""
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days_to_keep)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM email_history 
            WHERE DATE(timestamp) < ?
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def export_to_json(self, filepath: str = None) -> str:
        """Export all data to JSON for backup"""
        if filepath is None:
            filepath = f"email_memory_backup_{datetime.date.today()}.json"
        
        conn = sqlite3.connect(self.db_path)
        
        # Export all tables
        data = {}
        
        # Email history
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM email_history")
        columns = [desc[0] for desc in cursor.description]
        data['email_history'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # User context
        cursor.execute("SELECT * FROM user_context")
        columns = [desc[0] for desc in cursor.description]
        data['user_context'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Patterns
        cursor.execute("SELECT * FROM conversation_patterns")
        columns = [desc[0] for desc in cursor.description]
        data['conversation_patterns'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return filepath

# Example usage and testing
if __name__ == "__main__":
    # Initialize memory manager
    memory = EmailMemoryManager("test_email_memory.db")
    
    # Test storing an email decision
    test_email = EmailRecord(
        email_id="test_123",
        author="john@example.com",
        subject="Test meeting request",
        classification="RESPOND",
        reasoning="Direct meeting request needs response",
        thread_summary="Meeting request for project discussion",
        timestamp=datetime.datetime.now()
    )
    
    success = memory.store_email_decision(test_email)
    print(f"Stored email decision: {success}")
    
    # Test retrieving history
    history = memory.get_author_history("john@example.com")
    print(f"Author history: {len(history)} records")
    
    # Test context storage
    memory.update_user_context("preferred_meeting_time", "2pm-4pm", "scheduling")
    pref = memory.get_user_context("preferred_meeting_time")
    print(f"User preference: {pref}")
    
    # Test daily summary
    summary = memory.get_daily_summary()
    print(f"Daily summary: {summary}")
    
    # Test formatted history for prompts
    formatted = memory.format_author_history_for_prompt("john@example.com")
    print(f"Formatted history:\n{formatted}")