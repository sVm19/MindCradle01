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
            "subject": "Welcome to MindCradle",
            "html": f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #f0f0f0; border-radius: 16px;">
                  <h2 style="color: #E94B6F; font-size: 24px; margin-top: 0;">Welcome to MindCradle</h2>
                  <p>Your account is all set. Let's start your wellness journey today.</p>
                  
                  <div style="background: #FFF5F7; border: 1px solid #FFD3DC; padding: 16px; border-radius: 12px; margin-top: 24px; margin-bottom: 24px;">
                    <h3 style="color: #E94B6F; margin-top: 0; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#E94B6F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 6px; display: inline-block;">
                        <polyline points="20 12 20 22 4 22 4 12"></polyline>
                        <rect x="2" y="7" width="20" height="5"></rect>
                        <line x1="12" y1="22" x2="12" y2="7"></line>
                        <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"></path>
                        <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"></path>
                      </svg>
                      Your 7-Day Free Trial is Active!
                    </h3>
                    <p style="margin: 0; font-size: 14px; color: #555; line-height: 1.5;">
                      As a new user, you have been automatically upgraded to <strong>MindCradle Premium</strong> for the next 7 days.
                      Enjoy unlimited daily routines, unlimited ARIA conversation, and detailed emotional analytics!
                    </p>
                  </div>

                  <a href="https://mindcradle.online/dashboard" style="background: #E94B6F; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 10px; font-weight: bold;">
                    Open Dashboard
                  </a>
                  <p style="margin-top: 30px; color: #666; font-size: 13px; border-t: 1px solid #f0f0f0; padding-top: 15px;">
                    Questions or feedback? Just reply to this email or contact us at <a href="mailto:support@mindcradle.online" style="color: #E94B6F;">support@mindcradle.online</a>
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
