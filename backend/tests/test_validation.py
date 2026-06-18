import unittest
from pydantic import ValidationError
from app.models.schemas import SignupRequest, MoodCreate, MoodLogRequest, JournalCreate, AIChatRequest
from app.utils.sanitizer import sanitize

class TestValidationAndSanitization(unittest.TestCase):
    
    def test_sanitizer_xss_sql_injection_length(self):
        # 1. HTML / XSS escaping
        xss_input = "<script>alert('xss')</script>"
        sanitized_xss = sanitize(xss_input)
        self.assertEqual(sanitized_xss, "alert(&#x27;xss&#x27;)")
        
        # 2. SQL injection escaping
        sql_input = "'; DROP TABLE users; --"
        sanitized_sql = sanitize(sql_input)
        self.assertEqual(sanitized_sql, "&#x27;; DROP TABLE users; --")
        
        # 3. Truncation to 5000 chars
        long_input = "a" * 10000
        sanitized_long = sanitize(long_input)
        self.assertEqual(len(sanitized_long), 5000)
        
        # 4. Unicode / Special characters / Emojis
        unicode_input = "Hello! 🌟 émojis & unicode test < >"
        sanitized_unicode = sanitize(unicode_input)
        self.assertEqual(sanitized_unicode, "Hello! 🌟 émojis &amp;amp; unicode test &amp;lt; &amp;gt;")
        
    def test_signup_validation(self):
        # Valid signup
        valid_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "passwordConfirm": "Password123!",
            "name": "John Doe <script>alert(1)</script>"
        }
        req = SignupRequest(**valid_data)
        self.assertEqual(req.email, "test@example.com")
        # Check sanitation of name
        self.assertEqual(req.name, "John Doe alert(1)")
        
        # Invalid email type
        invalid_email = dict(valid_data, email="123")
        with self.assertRaises(ValidationError):
            SignupRequest(**invalid_email)
            
        # Invalid password (no uppercase)
        invalid_pwd_upper = dict(valid_data, password="password123!", passwordConfirm="password123!")
        with self.assertRaises(ValidationError):
            SignupRequest(**invalid_pwd_upper)
            
        # Invalid password (no digit)
        invalid_pwd_digit = dict(valid_data, password="Password!", passwordConfirm="Password!")
        with self.assertRaises(ValidationError):
            SignupRequest(**invalid_pwd_digit)
            
        # Invalid password (no special character)
        invalid_pwd_spec = dict(valid_data, password="Password123", passwordConfirm="Password123")
        with self.assertRaises(ValidationError):
            SignupRequest(**invalid_pwd_spec)
            
        # Invalid password (too short)
        invalid_pwd_short = dict(valid_data, password="P1!", passwordConfirm="P1!")
        with self.assertRaises(ValidationError):
            SignupRequest(**invalid_pwd_short)
            
    def test_mood_validation(self):
        # Valid mood
        valid_mood = {"level": 7, "note": "Feeling great! <3"}
        req = MoodCreate(**valid_mood)
        self.assertEqual(req.level, 7)
        self.assertEqual(req.note, "Feeling great! &amp;lt;3")
        
        # Out of bounds mood levels
        with self.assertRaises(ValidationError):
            MoodCreate(level=0, note="test")
        with self.assertRaises(ValidationError):
            MoodCreate(level=11, note="test")
            
        # Sanitization & validation on MoodLogRequest
        req_log = MoodLogRequest(level=5, notes="Some notes <script>")
        self.assertEqual(req_log.notes, "Some notes")
            
    def test_journal_validation(self):
        # Valid journal
        valid_journal = {
            "prompt": "What went well?",
            "content": "I completed my task! 🚀 <script>",
        }
        req = JournalCreate(**valid_journal)
        self.assertEqual(req.content, "I completed my task! 🚀")
        
        # Empty journal content
        with self.assertRaises(ValidationError):
            JournalCreate(prompt="test", content="")
            
    def test_ai_chat_validation(self):
        # Empty message
        with self.assertRaises(ValidationError):
            AIChatRequest(message="")
            
        # Sanitized message
        req = AIChatRequest(message="Hello ARIA! <script>")
        self.assertEqual(req.message, "Hello ARIA!")

if __name__ == "__main__":
    unittest.main()
