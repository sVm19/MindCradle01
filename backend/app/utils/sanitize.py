from bleach import clean
import html

def sanitize_text(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user text input
    - Remove HTML tags
    - Escape dangerous characters
    - Limit length
    """
    if not text:
        return ""
    
    # Strip all HTML tags (keep only text)
    cleaned = clean(text, tags=[], strip=True)
    
    # Escape any remaining special characters
    escaped = html.escape(cleaned)
    
    # Limit length
    return escaped[:max_length].strip()

def sanitize_journal_entry(text: str) -> str:
    """Sanitize journal entries (same as text)"""
    return sanitize_text(text, max_length=10000)

def sanitize_mood_notes(text: str) -> str:
    """Sanitize mood notes"""
    return sanitize_text(text, max_length=500)
