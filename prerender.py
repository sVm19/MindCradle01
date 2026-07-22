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

# Extract content from simple static components (About, Features)
def extract_tsx_content(page_name):
    filepath = os.path.join(FRONTEND_DIR, 'src', 'app', 'pages', f'{page_name}.tsx')
    if not os.path.exists(filepath):
        print(f"WARNING: Source file {filepath} not found for pre-rendering fallback.")
        return ""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Grab return block content inside the component
    match = re.search(r'return\s*\(\s*<div[^>]*>([\s\S]*?)</div>\s*\);\s*\}', content)
    if not match:
        match = re.search(r'return\s*\(\s*([\s\S]*?)\s*\);\s*\}', content)
        
    if not match:
        print(f"WARNING: Could not parse return block in {filepath}")
        return ""
        
    html = match.group(1)
    
    # Remove SEO tags
    html = re.sub(r'<SEO[\s\S]*?/>', '', html)
    
    # Replace React date placeholder
    html = html.replace('{todayDate}', 'June 28, 2026')
    
    # Remove React-specific comments
    html = re.sub(r'\{\/\*[\s\S]*?\*\/\s*\}', '', html)
    
    # Strip layout classNames and inline styles
    html = re.sub(r'\s*className="[^"]*"', '', html)
    html = re.sub(r'\s*style=\{\{[\s\S]*?\}\}', '', html)
    
    # Replace Lucide icons <Icon ... /> with empty space
    html = re.sub(r'<[A-Z][a-zA-Z0-9]*\s*[^>]*/>', '', html)
    
    # Replace Link tags with plain anchors
    html = re.sub(r'<Link\s+to="([^"]*)"([^>]*)>', r'<a href="\1"\2>', html)
    html = html.replace('</Link>', '</a>')
    
    # Clean up empty lines
    html = re.sub(r'\n\s*\n', '\n', html)
    
    return html.strip()

# Extract content from legal components (Privacy, Terms, Refund)
def extract_legal_content(page_name):
    filepath = os.path.join(FRONTEND_DIR, 'src', 'app', 'pages', f'{page_name}.tsx')
    if not os.path.exists(filepath):
        print(f"WARNING: Source file {filepath} not found for pre-rendering fallback.")
        return ""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Match starting from <div className="w-full" style={{ marginLeft: '2rem' ... }} to the matching closing div
    match = re.search(r'(<div\s+className="w-full"\s+style=\{\{\s*marginLeft:\s*\'2rem\'[\s\S]*?)</div>\s*</div>\s*\);\s*\}', content)
    if not match:
        match = re.search(r'(<div\s+className="w-full"[\s\S]*?)</div>\s*</div>', content)
        
    if not match:
        print(f"WARNING: Could not parse legal block in {filepath}")
        return ""
        
    html = match.group(1)
    
    # Replace React date placeholder
    html = html.replace('{todayDate}', 'June 28, 2026')
    
    # Remove React-specific comments
    html = re.sub(r'\{\/\*[\s\S]*?\*\/\s*\}', '', html)
    
    # Strip layout classNames and inline styles
    html = re.sub(r'\s*className="[^"]*"', '', html)
    html = re.sub(r'\s*style=\{\{[\s\S]*?\}\}', '', html)
    
    # Replace Link tags with plain anchors
    html = re.sub(r'<Link\s+to="([^"]*)"([^>]*)>', r'<a href="\1"\2>', html)
    html = html.replace('</Link>', '</a>')
    
    # Clean up empty lines
    html = re.sub(r'\n\s*\n', '\n', html)
    
    return html.strip()

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
about_content = extract_tsx_content('About')
render_page("/about", "About Us — MindCradle", "Learn about the mission behind MindCradle — a premium, privacy-first companion built for emotional resilience and self-discovery.", about_content)

# --- Features ---
features_content = extract_tsx_content('Features')
render_page("/features", "Features — MindCradle", "Explore MindCradle's key capabilities: Mood Tracking, Daily Rituals, Guided Journaling, and AI Insights.", features_content)

# --- Pricing (Curated Long-form HTML for rich E-E-A-T indexing) ---
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
      <li>✓ Basic Mood Logging & Trends</li>
      <li>✓ 1 Active Daily Ritual (Morning or Evening)</li>
      <li>✓ Limited ARIA Chat (5 messages/day)</li>
      <li>✓ 7-Day Context History Window</li>
    </ul>
    <a href="https://mindcradle.online/login" style="display: block; padding: 0.75rem; background: rgba(255,255,255,0.1); color: #ffffff; border-radius: 9999px; text-decoration: none; font-weight: 600; font-size: 0.9rem;">Get Started Free</a>
  </div>
  <div style="background: linear-gradient(135deg, rgba(240,147,160,0.08), rgba(244,117,162,0.08)); padding: 2rem; border-radius: 16px; border: 1px solid rgba(240,147,160,0.25); text-align: center; position: relative;">
    <div style="position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #E94B6F; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em;">RECOMMENDED</div>
    <h2 style="font-size: 1.5rem; font-weight: 400; margin-bottom: 0.5rem; color: #f093a0;">MindCradle Premium</h2>
    <p style="font-size: 2rem; font-weight: 300; margin-bottom: 1.5rem; color: #ffffff;">$9.99 <span style="font-size: 0.9rem; color: rgba(255,255,255,0.6);">/ month</span></p>
    <ul style="list-style: none; padding: 0; text-align: left; margin-bottom: 2rem; font-size: 0.9rem; color: rgba(255,255,255,0.75); line-height: 1.8;">
      <li>✓ <strong>Unlimited</strong> ARIA memory & messages</li>
      <li>✓ Compounding Personal Knowledge Graph (PKG)</li>
      <li>✓ Monthly/Seasonal Personal Solstice Letters</li>
      <li>✓ Advanced Emotion Analytics & Theme Spotting</li>
      <li>✓ Hybrid Semantic Search across all historical logs</li>
    </ul>
    <a href="https://mindcradle.online/login" style="display: block; padding: 0.75rem; background: #ffffff; color: #05020c; border-radius: 9999px; text-decoration: none; font-weight: 700; font-size: 0.9rem; box-shadow: 0 4px 15px rgba(233,75,111,0.2);">Start 7-Day Free Trial</a>
  </div>
</div>

<section style="margin-bottom: 3rem; background: rgba(255,255,255,0.02); padding: 2rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06);">
  <h2 style="font-size: 1.6rem; font-weight: 400; margin-bottom: 1.5rem; text-align: center; color: #f093a0;">Why Upgrade to Premium?</h2>
  <p style="line-height: 1.7; color: rgba(255,255,255,0.8); margin-bottom: 1rem;">
    While the Free plan provides basic tracking tools for self-awareness, MindCradle Premium unlocks the full potential of our **Compounding Intelligence Engine**. Rather than treating your mood logs and journals as static records, Premium builds a secure, structured database of your life. 
  </p>
  <p style="line-height: 1.7; color: rgba(255,255,255,0.8);">
    With **Longitudinal Relational Memory**, ARIA remembers connections across weeks and months, recognizing cycles in your stress and reminding you of coping mechanisms that worked in previous chapters. Your subscription directly supports a privacy-first wellness platform, and your data is never sold or shared.
  </p>
</section>

<section style="margin-bottom: 2.5rem;">
  <h2 style="font-size: 1.6rem; font-weight: 400; margin-bottom: 1.5rem; text-align: center;">Frequently Asked Questions</h2>
  <div style="display: grid; gap: 1.25rem;">
    <div style="background: rgba(255,255,255,0.03); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
      <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem; color: #ffffff;">How does the 7-day free trial work?</h3>
      <p style="font-size: 0.9rem; color: rgba(255,255,255,0.7); line-height: 1.6;">You receive complete access to all Premium features immediately for 7 days. If you cancel before the trial concludes, you will not be charged. You can cancel with one click from your billing page.</p>
    </div>
    <div style="background: rgba(255,255,255,0.03); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
      <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem; color: #ffffff;">Is my emotional and journal data private?</h3>
      <p style="font-size: 0.9rem; color: rgba(255,255,255,0.7); line-height: 1.6;">Absolutely. MindCradle is privacy-first. We protect your data with end-to-end encryption in transit and at rest. We never sell, rent, or share your journals or conversation logs with third parties or advertising brokers.</p>
    </div>
    <div style="background: rgba(255,255,255,0.03); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
      <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem; color: #ffffff;">Can I cancel my subscription anytime?</h3>
      <p style="font-size: 0.9rem; color: rgba(255,255,255,0.7); line-height: 1.6;">Yes. You can cancel your subscription easily through your profile settings page. Your access will remain active until the end of your paid billing period, and you will not be billed again.</p>
    </div>
  </div>
</section>
"""
render_page("/pricing", "Pricing — MindCradle", "Choose the right plan for your wellness journey. Start with our free tier or upgrade to Premium for unlimited ARIA memory and analytics.", pricing_content)

# --- Privacy ---
privacy_content = extract_legal_content('Privacy')
render_page("/privacy", "Privacy Policy — MindCradle", "Your emotional privacy is our priority. Read our privacy policy to understand how we secure your data.", privacy_content)

# --- Terms ---
terms_content = extract_legal_content('Terms')
render_page("/terms", "Terms of Service — MindCradle", "Read the terms of service governing your use of the MindCradle platform and services.", terms_content)

# --- Refund ---
refund_content = extract_legal_content('Refund')
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
