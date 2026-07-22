import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Response

from app.data.blog_data import BLOG_POSTS
from app.data.docs_data import DOCS_PAGES

router = APIRouter()
logger = logging.getLogger(__name__)

# Base host URL
BASE_URL = "https://mindcradle.online"

# ── Sitemap Index ─────────────────────────────────────────────────────────────

@router.get("/seo/sitemap.xml")
async def get_sitemap_index():
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>{BASE_URL}/sitemap-pages.xml</loc>
  </sitemap>
  <sitemap>
    <loc>{BASE_URL}/sitemap-blog.xml</loc>
  </sitemap>
  <sitemap>
    <loc>{BASE_URL}/sitemap-docs.xml</loc>
  </sitemap>
</sitemapindex>"""
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=900"})

# ── Split Sitemaps ─────────────────────────────────────────────────────────────

@router.get("/seo/sitemap-pages.xml")
async def get_sitemap_pages():
    # Public static pages
    pages = [
        {"path": "", "priority": "1.0", "changefreq": "daily"},
        {"path": "/features", "priority": "0.9", "changefreq": "monthly"},
        {"path": "/about", "priority": "0.8", "changefreq": "monthly"},
        {"path": "/pricing", "priority": "0.9", "changefreq": "weekly"},
        {"path": "/blog", "priority": "0.8", "changefreq": "daily"},
        {"path": "/docs", "priority": "0.7", "changefreq": "daily"},
        {"path": "/privacy", "priority": "0.5", "changefreq": "monthly"},
        {"path": "/terms", "priority": "0.5", "changefreq": "monthly"},
        {"path": "/refund", "priority": "0.3", "changefreq": "monthly"},
    ]
    
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    xml_items = []
    for page in pages:
        xml_items.append(f"""  <url>
    <loc>{BASE_URL}{page['path']}</loc>
    <lastmod>{today_str}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>""")
        
    xml_content = "\n".join(xml_items)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_content}
</urlset>"""
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=900"})


@router.get("/seo/sitemap-blog.xml")
async def get_sitemap_blog():
    xml_items = []
    for post in BLOG_POSTS:
        if post.get("draft"):
            continue
            
        # Parse lastmod
        try:
            dt = datetime.fromisoformat(post["modified_at"].replace("Z", "+00:00"))
            mod_date = dt.strftime("%Y-%m-%d")
        except Exception:
            mod_date = datetime.utcnow().strftime("%Y-%m-%d")
            
        xml_items.append(f"""  <url>
    <loc>{BASE_URL}/blog/{post['slug']}</loc>
    <lastmod>{mod_date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")
        
    xml_content = "\n".join(xml_items)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_content}
</urlset>"""
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=900"})


@router.get("/seo/sitemap-docs.xml")
async def get_sitemap_docs():
    xml_items = []
    for doc in DOCS_PAGES:
        if doc.get("draft"):
            continue
            
        try:
            dt = datetime.fromisoformat(doc["modified_at"].replace("Z", "+00:00"))
            mod_date = dt.strftime("%Y-%m-%d")
        except Exception:
            mod_date = datetime.utcnow().strftime("%Y-%m-%d")
            
        xml_items.append(f"""  <url>
    <loc>{BASE_URL}/docs/{doc['slug']}</loc>
    <lastmod>{mod_date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>""")
        
    xml_content = "\n".join(xml_items)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_content}
</urlset>"""
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=900"})

# ── Robots.txt ────────────────────────────────────────────────────────────────

@router.get("/seo/robots.txt")
async def get_robots_txt():
    robots = f"""# Allow all search engine crawlers and specifically encourage AI search bots
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /settings/
Disallow: /billing/
Disallow: /insights/
Disallow: /discoveries/
Disallow: /timeline/

# OpenAI GPTBot
User-agent: GPTBot
Allow: /
Disallow: /admin/
Disallow: /settings/
Disallow: /billing/
Disallow: /insights/
Disallow: /discoveries/
Disallow: /timeline/

# Anthropic ClaudeBot
User-agent: ClaudeBot
Allow: /
Disallow: /admin/
Disallow: /settings/
Disallow: /billing/
Disallow: /insights/
Disallow: /discoveries/
Disallow: /timeline/

# Perplexity AI Bot
User-agent: PerplexityBot
Allow: /
Disallow: /admin/
Disallow: /settings/
Disallow: /billing/
Disallow: /insights/
Disallow: /discoveries/
Disallow: /timeline/

# Google AI Extended (Gemini)
User-agent: Google-Extended
Allow: /
Disallow: /admin/
Disallow: /settings/
Disallow: /billing/
Disallow: /insights/
Disallow: /discoveries/
Disallow: /timeline/

# Applebot Extended (Apple Intelligence)
User-agent: Applebot-Extended
Allow: /
Disallow: /admin/
Disallow: /settings/
Disallow: /billing/
Disallow: /insights/
Disallow: /discoveries/
Disallow: /timeline/

Sitemap: {BASE_URL}/sitemap.xml
"""
    return Response(content=robots, media_type="text/plain", headers={"Cache-Control": "public, max-age=900"})

# ── RSS XML Feed ──────────────────────────────────────────────────────────────

@router.get("/seo/rss.xml")
async def get_rss_feed():
    xml_items = []
    for post in BLOG_POSTS:
        if post.get("draft"):
            continue
            
        # Format RFC 822 date for RSS (e.g. Mon, 15 Jun 2026 09:00:00 +0000)
        try:
            dt = datetime.fromisoformat(post["published_at"].replace("Z", "+00:00"))
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except Exception:
            pub_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
            
        # Simple HTML escape for XML
        summary_escaped = post["summary"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        xml_items.append(f"""    <item>
      <title>{post['title']}</title>
      <link>{BASE_URL}/blog/{post['slug']}</link>
      <description>{summary_escaped}</description>
      <pubDate>{pub_date}</pubDate>
      <guid>{BASE_URL}/blog/{post['slug']}</guid>
      <author>{post['author']['name']}</author>
    </item>""")
        
    xml_content = "\n".join(xml_items)
    xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>MindCradle Blog</title>
    <link>{BASE_URL}/blog</link>
    <description>Insights on persistent AI memory, longitudinal context, and relational wellness companions.</description>
    <language>en-us</language>
    <atom:link href="{BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
{xml_content}
  </channel>
</rss>"""
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=900"})

# ── Content REST Endpoints ────────────────────────────────────────────────────

@router.get("/blog")
async def get_all_blog_posts():
    # Return metadata only for listing page
    return [
        {
            "slug": p["slug"],
            "title": p["title"],
            "summary": p["summary"],
            "category": p["category"],
            "tags": p["tags"],
            "author": p["author"],
            "published_at": p["published_at"],
            "image": p["image"],
            "read_time_mins": p["read_time_mins"]
        }
        for p in BLOG_POSTS if not p.get("draft")
    ]


@router.get("/blog/{slug}")
async def get_blog_post_by_slug(slug: str):
    for post in BLOG_POSTS:
        if post["slug"] == slug and not post.get("draft"):
            return post
    raise HTTPException(status_code=404, detail="Blog post not found")


@router.get("/docs")
async def get_all_docs():
    # Exclude drafts and return hierarchy metadata
    return [
        {
            "slug": d["slug"],
            "title": d["title"],
            "category": d["category"],
            "order": d["order"]
        }
        for d in DOCS_PAGES if not d.get("draft")
    ]


@router.get("/docs/{slug}")
async def get_doc_by_slug(slug: str):
    for doc in DOCS_PAGES:
        if doc["slug"] == slug and not doc.get("draft"):
            return doc
    raise HTTPException(status_code=404, detail="Documentation page not found")
