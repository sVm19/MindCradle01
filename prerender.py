#!/usr/bin/env python3
import os
import sys
import re

print("================ PRE-RENDER START ================")
print(f"Current Working Directory: {os.getcwd()}")
print(f"Python Version: {sys.version}")

# Preflight monorepo checks
BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend')
DIST_DIR = os.path.join(FRONTEND_DIR, 'dist')
TEMPLATE_PATH = os.path.join(DIST_DIR, 'index.html')

print(f"Backend directory exists: {os.path.exists(BACKEND_DIR)}")
print(f"Frontend directory exists: {os.path.exists(FRONTEND_DIR)}")
print(f"Dist directory exists: {os.path.exists(DIST_DIR)}")

if not os.path.exists(TEMPLATE_PATH):
    print(f"ERROR: Template file not found at {TEMPLATE_PATH}. Did you run 'vite build' first?")
    sys.exit(1)

# Import backend data dynamically
sys.path.append(BACKEND_DIR)
try:
    from app.data.blog_data import BLOG_POSTS
    from app.data.docs_data import DOCS_PAGES
    print(f"Successfully loaded {len(BLOG_POSTS)} blog posts and {len(DOCS_PAGES)} docs pages.")
except Exception as e:
    print(f"ERROR: Failed to load backend data: {e}")
    sys.exit(1)

with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    template_html = f.read()

# Markdown to HTML converter
def md_to_html(md_text):
    if not md_text:
        return ""
    
    html = md_text.strip()
    # Code blocks
    html = re.sub(r'```(?:[a-zA-Z0-9_-]+)?\n(.*?)\n```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    # Headings
    html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # Lists (Unordered)
    html = re.sub(r'^\*\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    # Wrap consecutive lists in ul
    html = re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\0</ul>', html, flags=re.DOTALL)
    # Clean up duplicate wrapper side-effects
    html = html.replace('<ul>\n<ul>', '<ul>').replace('</ul>\n</ul>', '</ul>')
    
    # Paragraphs (split by double newlines)
    paragraphs = html.split('\n\n')
    p_htmls = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Skip if already wrapped in block elements
        if any(p.startswith(tag) for tag in ('<h', '<pre', '<ul', '<ol', '<li')):
            p_htmls.append(p)
        else:
            # Simple line break inside paragraphs
            p_htmls.append(f"<p>{p.replace('\n', '<br>')}</p>")
            
    return '\n'.join(p_htmls)

def render_page(path_sub, title, description, content_html):
    # Set up clean URL
    canonical = f"https://mindcradle.online{path_sub}"
    
    # Replacement of metadata
    html = template_html
    html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html)
    
    # Meta Description
    html = re.sub(
        r'<meta\s+name="description"\s+content=".*?"', 
        f'<meta name="description" content="{description}"', 
        html
    )
    
    # Canonical link
    html = re.sub(
        r'<link\s+rel="canonical"\s+href=".*?"', 
        f'<link rel="canonical" href="{canonical}"', 
        html
    )
    
    # Open Graph properties
    html = re.sub(r'<meta\s+property="og:title"\s+content=".*?"', f'<meta property="og:title" content="{title}"', html)
    html = re.sub(r'<meta\s+property="og:description"\s+content=".*?"', f'<meta property="og:description" content="{description}"', html)
    html = re.sub(r'<meta\s+property="og:url"\s+content=".*?"', f'<meta property="og:url" content="{canonical}"', html)
    
    # Twitter tags
    html = re.sub(r'<meta\s+name="twitter:title"\s+content=".*?"', f'<meta name="twitter:title" content="{title}"', html)
    html = re.sub(r'<meta\s+name="twitter:description"\s+content=".*?"', f'<meta name="twitter:description" content="{description}"', html)
    
    # Replace main landmark fallback
    main_pattern = r'<main id="main-content" role="main" style="[^"]*">[\s\S]*?</main>'
    main_replacement = f'<main id="main-content" role="main" style="padding: 2rem 1.5rem; max-width: 900px; margin: 0 auto; color: #ffffff; font-family: sans-serif;">\n{content_html}\n</main>'
    html = re.sub(main_pattern, main_replacement, html)
    
    # Output path
    out_dir = os.path.join(DIST_DIR, path_sub.lstrip('/'))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'index.html')
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Generated pre-rendered file: {out_file}")

# 1. PRE-RENDER STATIC PAGES
# --- About ---
about_content = """
<header style="text-align: center; margin-bottom: 2.5rem;">
  <h1 style="font-size: 2.2rem; font-weight: 400; margin-bottom: 1rem; color: #ffffff;">About MindCradle</h1>
  <p style="font-size: 1.1rem; color: rgba(255,255,255,0.7); max-width: 640px; margin: 0 auto;">Empowering people to understand themselves better through daily wellness practices.</p>
</header>
<section style="margin-bottom: 2.5rem; background: rgba(255,255,255,0.03); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
  <h2 style="color: #f093a0; font-size: 1.5rem; font-weight: 400; margin-bottom: 1rem;">Our Mission</h2>
  <p style="line-height: 1.7; color: rgba(255,255,255,0.85);">We believe mental wellness should be accessible, private, and empowering. MindCradle is built to help you discover patterns in your emotions, build sustainable habits, and develop a deeper connection with yourself.</p>
</section>
<section style="margin-bottom: 2.5rem;">
  <h2 style="font-size: 1.5rem; font-weight: 400; margin-bottom: 1.25rem;">Our Core Values</h2>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.25rem;">
    <div style="background: rgba(255,255,255,0.05); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
      <h3 style="color: #4ecdc4; font-size: 1.1rem; margin-bottom: 0.5rem;">🔒 Privacy First</h3>
      <p style="font-size: 0.88rem; color: rgba(255,255,255,0.75); line-height: 1.6;">Your journals, logs, and emotional data belong to you. We protect your data with end-to-end encryption and never monetize or share it.</p>
    </div>
    <div style="background: rgba(255,255,255,0.05); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
      <h3 style="color: #ffd166; font-size: 1.1rem; margin-bottom: 0.5rem;">🌱 Compounding Self-Discovery</h3>
      <p style="font-size: 0.88rem; color: rgba(255,255,255,0.75); line-height: 1.6;">We value longitudinal connection. MindCradle connects your daily intentions and mood states across chapters to highlight long-term emotional evolution.</p>
    </div>
  </div>
</section>
"""
render_page("/about", "About Us — MindCradle", "Learn about the mission behind MindCradle — a premium, privacy-first companion built for emotional resilience and self-discovery.", about_content)

# --- Features ---
features_content = """
<header style="text-align: center; margin-bottom: 2.5rem;">
  <h1 style="font-size: 2.2rem; font-weight: 400; margin-bottom: 1rem; color: #ffffff;">MindCradle Features</h1>
  <p style="font-size: 1.1rem; color: rgba(255,255,255,0.7); max-width: 640px; margin: 0 auto;">Everything you need to track your thoughts, align your energy, and build a consistent routine.</p>
</header>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem;">
  <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
    <h3 style="color: #f093a0; font-size: 1.2rem; margin-bottom: 0.75rem;">01. 30-Second Micro-Checkins</h3>
    <p style="font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.6;">Log mood, sleep, and energy levels seamlessly in under 30 seconds. Spot recurring emotional trends over weeks and months.</p>
  </div>
  <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
    <h3 style="color: #4ecdc4; font-size: 1.2rem; margin-bottom: 0.75rem;">02. Longitudinal AI Memory (ARIA)</h3>
    <p style="font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.6;">ARIA synthesizes your journal reflections across weeks to uncover hidden burnout risks, behavioral shifts, and growth milestones.</p>
  </div>
  <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
    <h3 style="color: #8b7cf8; font-size: 1.2rem; margin-bottom: 0.75rem;">03. Guided Journal & Hybrid Search</h3>
    <p style="font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.6;">Express your thoughts with structured prompts. Search past entries naturally using semantic vector search—ask questions like 'When did I feel most relaxed last month?'</p>
  </div>
  <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
    <h3 style="color: #ffd166; font-size: 1.2rem; margin-bottom: 0.75rem;">04. Guided Morning & Evening Rituals</h3>
    <p style="font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.6;">Ground your morning with intent setting and wind down your evening with ambient reflection. Build healthy habits with daily streak tracking.</p>
  </div>
</div>
"""
render_page("/features", "Features — MindCradle", "Explore MindCradle's key capabilities: Mood Tracking, Daily Rituals, Guided Journaling, and AI Insights.", features_content)

# --- Pricing ---
pricing_content = """
<header style="text-align: center; margin-bottom: 2.5rem;">
  <h1 style="font-size: 2.2rem; font-weight: 400; margin-bottom: 1rem; color: #ffffff;">Pricing Plans</h1>
  <p style="font-size: 1.1rem; color: rgba(255,255,255,0.7); max-width: 640px; margin: 0 auto;">Choose the right plan for your wellness journey. Start for free or unlock unlimited growth insights.</p>
</header>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 2rem; max-width: 800px; margin: 0 auto 3rem;">
  <div style="background: rgba(255,255,255,0.03); padding: 2rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); text-align: center;">
    <h2 style="font-size: 1.5rem; font-weight: 400; margin-bottom: 0.5rem;">MindCradle Free</h2>
    <p style="font-size: 2rem; font-weight: 300; margin-bottom: 1.5rem; color: #ffffff;">$0 <span style="font-size: 0.9rem; color: rgba(255,255,255,0.6);">/ month</span></p>
    <ul style="list-style: none; padding: 0; text-align: left; margin-bottom: 2rem; font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.8;">
      <li>✓ Basic Mood Logging</li>
      <li>✓ 1 Active Daily Ritual</li>
      <li>✓ Limited ARIA Chat (5 messages/day)</li>
      <li>✓ 7-Day History Window</li>
    </ul>
    <a href="https://mindcradle.online/login" style="display: block; padding: 0.75rem; background: rgba(255,255,255,0.1); color: #ffffff; border-radius: 9999px; text-decoration: none; font-weight: 600; font-size: 0.9rem;">Get Started</a>
  </div>
  <div style="background: linear-gradient(135deg, rgba(240,147,160,0.08), rgba(244,117,162,0.08)); padding: 2rem; border-radius: 16px; border: 1px solid rgba(240,147,160,0.25); text-align: center; position: relative;">
    <div style="position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #E94B6F; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em;">RECOMMENDED</div>
    <h2 style="font-size: 1.5rem; font-weight: 400; margin-bottom: 0.5rem; color: #f093a0;">MindCradle Premium</h2>
    <p style="font-size: 2rem; font-weight: 300; margin-bottom: 1.5rem; color: #ffffff;">$9.99 <span style="font-size: 0.9rem; color: rgba(255,255,255,0.6);">/ month</span></p>
    <ul style="list-style: none; padding: 0; text-align: left; margin-bottom: 2rem; font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.8;">
      <li>✓ <strong>Unlimited</strong> ARIA memory & messages</li>
      <li>✓ Compounding Personal Knowledge Graph</li>
      <li>✓ Monthly/Seasonal Solstice Letter</li>
      <li>✓ Advanced Emotion Analytics & Trends</li>
      <li>✓ Hybrid Semantic Search of all history</li>
    </ul>
    <a href="https://mindcradle.online/login" style="display: block; padding: 0.75rem; background: #ffffff; color: #05020c; border-radius: 9999px; text-decoration: none; font-weight: 700; font-size: 0.9rem; box-shadow: 0 4px 15px rgba(233,75,111,0.2);">Start 7-Day Free Trial</a>
  </div>
</div>
"""
render_page("/pricing", "Pricing — MindCradle", "Choose the right plan for your wellness journey. Start with our free tier or upgrade to Premium for unlimited ARIA memory and analytics.", pricing_content)

# --- Privacy ---
privacy_content = """
<h1>Privacy Policy</h1>
<p style="font-size: 0.9rem; color: rgba(255,255,255,0.6); margin-bottom: 2rem;">Last Updated: June 28, 2026</p>
<section style="line-height: 1.7; color: rgba(255,255,255,0.85); space-y-4;">
  <h2>1. Data Collection & Privacy First Approach</h2>
  <p>MindCradle is built on a privacy-first foundation. We gather minimal personal information required to run the core features of the dashboard, including credentials, daily check-in logs, and journal reflections. Your data is end-to-end encrypted.</p>
  <h2>2. AI Integrations & Prompt Privacy</h2>
  <p>All interactions with our AI companion ARIA are processed using secure APIs. We do not use your personal entries to train public LLM models.</p>
  <h2>3. Your Rights</h2>
  <p>You have full ownership of your data. You can export your history or delete your account permanently with a single click in your settings.</p>
</section>
"""
render_page("/privacy", "Privacy Policy — MindCradle", "Your emotional privacy is our priority. Read our privacy policy to understand how we secure your data.", privacy_content)

# --- Terms ---
terms_content = """
<h1>Terms of Service</h1>
<p style="font-size: 0.9rem; color: rgba(255,255,255,0.6); margin-bottom: 2rem;">Last Updated: June 28, 2026</p>
<section style="line-height: 1.7; color: rgba(255,255,255,0.85); space-y-4;">
  <h2>1. Use of Services</h2>
  <p>By registering for a MindCradle account, you agree to these Terms of Service. MindCradle is a self-reflection wellness tool and is not a clinical therapeutic utility.</p>
  <h2>2. Subscriptions & Payments</h2>
  <p>Payments for Premium subscriptions are handled securely through Creem. Subscriptions renew automatically until cancelled.</p>
  <h2>3. Governing Law</h2>
  <p>These terms are governed by the applicable local regulations. You agree to use the service in compliance with all relevant laws.</p>
</section>
"""
render_page("/terms", "Terms of Service — MindCradle", "Read the terms of service governing your use of the MindCradle platform and services.", terms_content)

# --- Refund ---
refund_content = """
<h1>Refund Policy</h1>
<p style="font-size: 0.9rem; color: rgba(255,255,255,0.6); margin-bottom: 2rem;">Last Updated: June 28, 2026</p>
<section style="line-height: 1.7; color: rgba(255,255,255,0.85); space-y-4;">
  <h2>1. Subscription Cancellations</h2>
  <p>You can cancel your MindCradle Premium subscription at any time via the billing dashboard. Your access will remain active until the end of your current billing period.</p>
  <h2>2. Refund Requests</h2>
  <p>If you are not satisfied with your purchase, you can request a refund within 14 days of your initial transaction by emailing support@mindcradle.online. Approved refunds will be credited back to your original payment method.</p>
</section>
"""
render_page("/refund", "Refund Policy — MindCradle", "Review our refund policy for MindCradle Premium subscription cancellations and refund requests.", refund_content)


# 2. PRE-RENDER DYNAMIC BLOG POSTS
blog_index_html = """
<header style="text-align: center; margin-bottom: 2.5rem;">
  <h1 style="font-size: 2.2rem; font-weight: 400; margin-bottom: 1rem; color: #ffffff;">MindCradle Blog</h1>
  <p style="font-size: 1.1rem; color: rgba(255,255,255,0.7); max-width: 640px; margin: 0 auto;">Insights on persistent AI memory, longitudinal context, and relational wellness companions.</p>
</header>
<div style="display: grid; gap: 2rem;">
"""

for post in BLOG_POSTS:
    if post.get("draft"):
        continue
    
    slug = post["slug"]
    title = post["title"]
    summary = post["summary"]
    published = post["published_at"][:10]
    category = post["category"]
    
    # Add to index list
    blog_index_html += f"""
  <article style="background: rgba(255,255,255,0.03); padding: 1.75rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06);">
    <span style="font-size: 0.8rem; color: #f093a0; font-weight: 600; text-transform: uppercase;">{category}</span>
    <h2 style="font-size: 1.4rem; font-weight: 400; margin: 0.5rem 0;"><a href="/blog/{slug}" style="color: #ffffff; text-decoration: none;">{title}</a></h2>
    <p style="font-size: 0.92rem; color: rgba(255,255,255,0.75); line-height: 1.6; margin-bottom: 1rem;">{summary}</p>
    <div style="font-size: 0.82rem; color: rgba(255,255,255,0.5);">Published: {published} | By {post['author']['name']}</div>
  </article>
"""
    
    # Pre-render specific post page
    post_body_html = md_to_html(post["content"])
    post_html = f"""
<article style="max-width: 760px; margin: 0 auto;">
  <p style="text-align: center; font-size: 0.85rem; color: #f093a0; font-weight: 600; text-transform: uppercase;">{category}</p>
  <h1 style="font-size: 2.4rem; font-weight: 400; text-align: center; margin-bottom: 1rem; color: #ffffff; line-height: 1.25;">{title}</h1>
  <p style="text-align: center; font-size: 0.88rem; color: rgba(255,255,255,0.5); margin-bottom: 2rem;">Published {published} | By {post['author']['name']} | {post['read_time_mins']} min read</p>
  <div style="line-height: 1.8; font-size: 1.05rem; color: rgba(255,255,255,0.85);">
    {post_body_html}
  </div>
  <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 3rem 0;">
  <div style="display: flex; align-items: center; gap: 1.25rem; background: rgba(255,255,255,0.03); padding: 1.5rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06);">
    <img src="{post['author']['avatar']}" alt="{post['author']['name']}" style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover;">
    <div>
      <h4 style="font-size: 1rem; font-weight: 600; margin: 0 0 0.25rem;">About {post['author']['name']}</h4>
      <p style="font-size: 0.85rem; color: rgba(255,255,255,0.65); margin: 0; line-height: 1.5;">{post['author']['bio']}</p>
    </div>
  </div>
  <div style="margin-top: 2rem; text-align: center;">
    <a href="/blog" style="font-size: 0.9rem; color: #f093a0; text-decoration: none; font-weight: 600;">← Back to Blog</a>
  </div>
</article>
"""
    render_page(f"/blog/{slug}", f"{title} — MindCradle Blog", summary, post_html)

blog_index_html += "</div>"
render_page("/blog", "Mindfulness & AI Memory Blog — MindCradle", "Explore insights on persistent AI memory, longitudinal context, and relational wellness companions on the MindCradle blog.", blog_index_html)


# 3. PRE-RENDER DYNAMIC DOCS PAGES
docs_index_html = """
<header style="text-align: center; margin-bottom: 2.5rem;">
  <h1 style="font-size: 2.2rem; font-weight: 400; margin-bottom: 1rem; color: #ffffff;">Developer Documentation</h1>
  <p style="font-size: 1.1rem; color: rgba(255,255,255,0.7); max-width: 640px; margin: 0 auto;">Learn how MindCradle's Compounding Intelligence Engine and Memory Protocol work under the hood.</p>
</header>
<div style="display: grid; gap: 1.5rem; max-width: 800px; margin: 0 auto;">
"""

for doc in DOCS_PAGES:
    if doc.get("draft"):
        continue
    
    slug = doc["slug"]
    title = doc["title"]
    category = doc["category"]
    
    # Add to index list
    docs_index_html += f"""
  <div style="background: rgba(255,255,255,0.03); padding: 1.25rem 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center;">
    <div>
      <span style="font-size: 0.75rem; color: #8b7cf8; font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 0.25rem;">{category}</span>
      <h3 style="font-size: 1.2rem; font-weight: 400; margin: 0;"><a href="/docs/{slug}" style="color: #ffffff; text-decoration: none;">{title}</a></h3>
    </div>
    <a href="/docs/{slug}" style="color: #8b7cf8; text-decoration: none; font-size: 0.9rem; font-weight: 600;">Read →</a>
  </div>
"""
    
    # Pre-render specific doc page
    doc_body_html = md_to_html(doc["content"])
    doc_html = f"""
<div style="display: flex; gap: 2rem; align-items: start;">
  <nav style="width: 220px; flex-shrink: 0; background: rgba(255,255,255,0.02); padding: 1.25rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); font-size: 0.88rem;">
    <h4 style="font-weight: 600; margin-top: 0; margin-bottom: 0.75rem;">Documentation</h4>
    <ul style="list-style: none; padding: 0; margin: 0; line-height: 1.8;">
      <li><a href="/docs" style="color: rgba(255,255,255,0.6); text-decoration: none;">Overview</a></li>
"""
    for d in DOCS_PAGES:
        if not d.get("draft"):
            doc_html += f'      <li><a href="/docs/{d["slug"]}" style="color: {"#8b7cf8" if d["slug"] == slug else "rgba(255,255,255,0.6)"}; text-decoration: none;">{d["title"]}</a></li>\n'
            
    doc_html += f"""
    </ul>
    <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05);">
      <a href="/blog" style="color: rgba(255,255,255,0.6); text-decoration: none;">← Back to Blog</a>
    </div>
  </nav>
  <div style="flex-grow: 1; min-width: 0; line-height: 1.8; font-size: 1rem; color: rgba(255,255,255,0.85);">
    {doc_body_html}
  </div>
</div>
"""
    render_page(f"/docs/{slug}", f"{title} — Developer Docs", f"MindCradle technical docs: {title}. Category: {category}", doc_html)

docs_index_html += "</div>"
render_page("/docs", "Developer Documentation — MindCradle", "Learn how MindCradle's Compounding Intelligence Engine and Memory Protocol work under the hood.", docs_index_html)

print("================ PRE-RENDER COMPLETE ================")
