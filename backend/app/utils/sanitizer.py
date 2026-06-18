from app.utils.sanitize import sanitize_text

def sanitize(text: str) -> str:
    """
    Sanitize all user string inputs by escaping HTML, trimming whitespace,
    and truncating to 5000 characters to prevent XSS, SQL injections,
    and overflow issues.
    """
    return sanitize_text(text)
