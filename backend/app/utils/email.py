import resend
import os
from app import config as settings

resend.api_key = settings.RESEND_API_KEY or os.getenv("RESEND_API_KEY")

def send_signup_welcome(user_email: str):
    """Send welcome email after successful signup"""
    try:
        email = resend.Emails.send({
            "from": "noreply@mindcradle.online",
            "to": user_email,
            "subject": "Welcome to MindCradle 🎉",
            "html": f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #E94B6F;">Welcome to MindCradle</h2>
                  <p>Your account is all set. Let's start your wellness journey.</p>
                  <a href="https://mindcradle.online/dashboard" style="background: #E94B6F; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 20px;">
                    Open Dashboard
                  </a>
                  <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    Questions? Email support@mindcradle.online
                  </p>
                </div>
              </body>
            </html>
            """
        })
        return email.get("id") is not None
    except Exception as e:
        print(f"Signup email failed: {str(e)}")
        return False

def send_password_reset_email(user_email: str, reset_link: str):
    """Send password reset email"""
    try:
        email = resend.Emails.send({
            "from": "noreply@mindcradle.online",
            "to": user_email,
            "subject": "Reset Your MindCradle Password",
            "html": f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #E94B6F;">Password Reset</h2>
                  <p>Click below to reset your password (expires in 15 minutes):</p>
                  <a href="{reset_link}" style="background: #E94B6F; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 20px;">
                    Reset Password
                  </a>
                  <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    If you didn't request this, ignore this email.
                  </p>
                </div>
              </body>
            </html>
            """
        })
        return email.get("id") is not None
    except Exception as e:
        print(f"Reset email failed: {str(e)}")
        return False

def send_magic_link_email(user_email: str, magic_link: str):
    """Send magic link for passwordless login"""
    try:
        email = resend.Emails.send({
            "from": "noreply@mindcradle.online",
            "to": user_email,
            "subject": "Your MindCradle Login Link",
            "html": f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #E94B6F;">Login to MindCradle</h2>
                  <p>Click below to login (expires in 15 minutes):</p>
                  <a href="{magic_link}" style="background: #E94B6F; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 20px;">
                    Login Now
                  </a>
                  <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    If you didn't request this, ignore this email.
                  </p>
                </div>
              </body>
            </html>
            """
        })
        return email.get("id") is not None
    except Exception as e:
        print(f"Magic link email failed: {str(e)}")
        return False
