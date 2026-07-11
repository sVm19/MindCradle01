import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router';
import { ai as aiApi } from '@/lib/api';
import SEO from '@/app/components/SEO';
import { Clock, Calendar, ArrowLeft, ArrowRight, Rss, User } from 'lucide-react';

interface Author {
  name: string;
  avatar: string;
  bio: string;
}

interface BlogPost {
  slug: string;
  title: string;
  summary: string;
  content: string;
  category: string;
  tags: string[];
  author: Author;
  published_at: string;
  modified_at: string;
  image: string;
  read_time_mins: number;
}

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>();
  const [post, setPost] = useState<BlogPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [allPosts, setAllPosts] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    setError(null);

    aiApi.getBlogPostBySlug(slug)
      .then((data) => {
        setPost(data);
      })
      .catch((err) => {
        console.error('Failed to load post:', err);
        setError('Article not found.');
      })
      .finally(() => {
        setLoading(false);
      });

    aiApi.getBlogPosts()
      .then((posts) => setAllPosts(posts))
      .catch(() => {});
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="max-w-md mx-auto text-center py-16 space-y-4">
        <h2 className="text-xl font-light text-text">Article Not Found</h2>
        <p className="text-xs text-text3 font-light">The blog article you are looking for does not exist or has been removed.</p>
        <Link to="/blog" className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent hover:underline">
          <ArrowLeft size={13} /> Back to Blog
        </Link>
      </div>
    );
  }

  // Related posts: pick up to 2 other posts in the same category or overlapping tags
  const relatedPosts = allPosts
    .filter((p) => p.slug !== post.slug)
    .filter((p) => p.category === post.category || p.tags.some((t: string) => post.tags.includes(t)))
    .slice(0, 2);

  // Pagination navigation (find current index in all posts)
  const currentIndex = allPosts.findIndex((p) => p.slug === post.slug);
  const prevPost = currentIndex > 0 ? allPosts[currentIndex - 1] : null;
  const nextPost = currentIndex < allPosts.length - 1 ? allPosts[currentIndex + 1] : null;

  // Generate Table of Contents items from the markdown content headings (##)
  const tocItems = post.content
    .split('\n')
    .filter((line) => line.trim().startsWith('## '))
    .map((line) => line.trim().substring(3));

  // Structured Data JSON-LD
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": post.title,
    "description": post.summary,
    "image": post.image,
    "datePublished": post.published_at,
    "dateModified": post.modified_at,
    "author": {
      "@type": "Person",
      "name": post.author.name
    },
    "publisher": {
      "@type": "Organization",
      "name": "MindCradle",
      "logo": {
        "@type": "ImageObject",
        "url": "https://mindcradle.online/mindcradle-logo.svg"
      }
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": `https://mindcradle.online/blog/${post.slug}`
    }
  };

  const breadcrumbsSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {
        "@type": "ListItem",
        "position": 1,
        "name": "Home",
        "item": "https://mindcradle.online"
      },
      {
        "@type": "ListItem",
        "position": 2,
        "name": "Blog",
        "item": "https://mindcradle.online/blog"
      },
      {
        "@type": "ListItem",
        "position": 3,
        "name": post.title,
        "item": `https://mindcradle.online/blog/${post.slug}`
      }
    ]
  };

  const formattedDate = new Date(post.published_at).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12 space-y-12 animate-fadeIn text-left">
      <SEO
        title={`${post.title} | MindCradle Blog`}
        description={post.summary}
        ogImage={post.image}
        schema={[articleSchema, breadcrumbsSchema]}
      />

      {/* Top Header Row with Back Button & RSS */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <Link to="/blog" className="inline-flex items-center gap-1.5 text-xs text-text3 hover:text-accent font-semibold transition-colors">
          <ArrowLeft size={14} /> Back to Blog
        </Link>
        <a href="/rss.xml" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-text3 hover:text-amber font-mono font-semibold transition-colors">
          <Rss size={14} /> RSS Feed
        </a>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
        {/* Left Column: Article Body (Spans 3 cols) */}
        <div className="lg:col-span-3 space-y-8">
          {/* Breadcrumbs */}
          <nav className="text-xs text-text3 font-mono flex flex-wrap items-center gap-2">
            <Link to="/" className="hover:text-accent transition-colors">Home</Link>
            <span>/</span>
            <Link to="/blog" className="hover:text-accent transition-colors">Blog</Link>
            <span>/</span>
            <span className="text-text2 truncate max-w-xs">{post.title}</span>
          </nav>

          {/* Heading */}
          <header className="space-y-4">
            <span className="text-[10px] bg-accent/10 border border-accent/20 text-accent px-3 py-1 rounded-full font-semibold tracking-wider uppercase font-mono inline-block">
              {post.category}
            </span>
            <h1 className="font-[family-name:var(--font-serif)] text-2xl sm:text-3xl md:text-4xl font-light text-text leading-tight">
              {post.title}
            </h1>
            <p className="text-sm text-text3 italic leading-relaxed font-light border-l-2 border-border pl-4">
              "{post.summary}"
            </p>
          </header>

          {/* Metadata Row */}
          <div className="flex items-center justify-between border-y border-border py-4 text-xs">
            {/* Author details */}
            <div className="flex items-center gap-3">
              <img
                src={post.author.avatar}
                alt={post.author.name}
                loading="lazy"
                width="36"
                height="36"
                className="w-9 h-9 rounded-full object-cover border border-border"
              />
              <div>
                <div className="font-semibold text-text">{post.author.name}</div>
                <div className="text-[10px] text-text3 font-mono">{formattedDate}</div>
              </div>
            </div>

            {/* Read duration */}
            <div className="text-text3 font-mono text-[10.5px]">
              {post.read_time_mins} min read
            </div>
          </div>

          {/* Featured Image */}
          <div className="rounded-[24px] overflow-hidden aspect-video border border-border shadow-xl">
            <img
              src={post.image}
              alt={post.title}
              width="900"
              height="506"
              className="object-cover w-full h-full"
            />
          </div>

          {/* Render Markdown Body */}
          <div className="prose prose-invert max-w-none pt-4 font-sans">
            {renderMarkdown(post.content)}
          </div>

          {/* Author Bio Box */}
          <div className="bg-bg2 border border-border rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-center sm:items-start gap-6 mt-12">
            <img
              src={post.author.avatar}
              alt={post.author.name}
              width="64"
              height="64"
              className="w-16 h-16 rounded-2xl object-cover border border-border shrink-0 shadow-lg"
            />
            <div className="space-y-2 text-center sm:text-left">
              <h3 className="font-[family-name:var(--font-serif)] text-[16px] font-semibold text-text">
                About the Author: {post.author.name}
              </h3>
              <p className="text-xs text-text3 font-light leading-relaxed">
                {post.author.bio}
              </p>
            </div>
          </div>

          {/* Pagination Navigation */}
          <div className="border-t border-border pt-8 flex items-center justify-between gap-4 text-xs font-semibold">
            {prevPost ? (
              <Link to={`/blog/${prevPost.slug}`} className="group flex flex-col items-start gap-1 max-w-[45%] text-left">
                <span className="text-[10px] text-text3 font-mono flex items-center gap-1"><ArrowLeft size={10} /> Previous</span>
                <span className="text-text2 hover:text-accent font-light leading-tight transition-colors line-clamp-1">{prevPost.title}</span>
              </Link>
            ) : (
              <div />
            )}

            {nextPost ? (
              <Link to={`/blog/${nextPost.slug}`} className="group flex flex-col items-end gap-1 max-w-[45%] text-right">
                <span className="text-[10px] text-text3 font-mono flex items-center gap-1">Next <ArrowRight size={10} /></span>
                <span className="text-text2 hover:text-accent font-light leading-tight transition-colors line-clamp-1">{nextPost.title}</span>
              </Link>
            ) : (
              <div />
            )}
          </div>
        </div>

        {/* Right Column: Table of Contents & Related Posts (Spans 1 col) */}
        <aside className="lg:col-span-1 space-y-10 lg:sticky lg:top-8 self-start">
          {/* Table of Contents */}
          {tocItems.length > 0 && (
            <div className="bg-bg2 border border-border rounded-3xl p-6 space-y-4">
              <h3 className="font-[family-name:var(--font-serif)] text-sm font-semibold text-text border-b border-border pb-2">
                Table of Contents
              </h3>
              <ul className="space-y-2.5 text-xs text-text3 font-mono font-light leading-relaxed">
                {tocItems.map((item, idx) => (
                  <li key={idx} className="hover:text-accent transition-colors flex items-start gap-1">
                    <span>✦</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Related Articles */}
          {relatedPosts.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-[family-name:var(--font-serif)] text-sm font-semibold text-text border-b border-border pb-2">
                Related Articles
              </h3>
              <div className="space-y-4">
                {relatedPosts.map((related) => (
                  <Link
                    key={related.slug}
                    to={`/blog/${related.slug}`}
                    className="block bg-bg2 border border-border rounded-2xl p-4 hover:border-accent/40 shadow-md hover:shadow-accent/5 transition-all group"
                  >
                    <div className="aspect-video rounded-xl overflow-hidden mb-3 border border-border">
                      <img
                        src={related.image}
                        alt={related.title}
                        width="300"
                        height="169"
                        className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
                      />
                    </div>
                    <h4 className="text-xs font-semibold text-text group-hover:text-accent transition-colors leading-tight line-clamp-2">
                      {related.title}
                    </h4>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

// ── Native Markdown Parser ───────────────────────────────────────────────────

function renderMarkdown(md: string) {
  const lines = md.split('\n');
  const elements: React.ReactNode[] = [];
  let inList = false;
  let listItems: string[] = [];

  const flushList = (key: number) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${key}`} className="list-disc pl-5 mb-4 text-xs sm:text-sm md:text-base space-y-1.5 font-light text-text2 leading-relaxed">
          {listItems.map((item, idx) => (
            <li key={idx} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ')) {
      inList = true;
      listItems.push(trimmed.substring(2));
      return;
    } else if (inList && !trimmed.startsWith('- ') && trimmed !== '') {
      inList = false;
      flushList(index);
    }

    if (trimmed === '') {
      return;
    }

    if (trimmed.startsWith('# ')) {
      elements.push(<h1 key={index} className="text-2xl sm:text-3xl md:text-4xl font-[family-name:var(--font-serif)] font-light text-text mt-8 mb-4 border-b border-border pb-2">{trimmed.substring(2)}</h1>);
    } else if (trimmed.startsWith('## ')) {
      elements.push(<h2 key={index} className="text-xl sm:text-2xl font-[family-name:var(--font-serif)] font-light text-text mt-6 mb-3">{trimmed.substring(3)}</h2>);
    } else if (trimmed.startsWith('### ')) {
      elements.push(<h3 key={index} className="text-lg sm:text-xl font-semibold text-text mt-4 mb-2">{trimmed.substring(4)}</h3>);
    } else {
      elements.push(
        <p key={index} className="mb-4 text-xs sm:text-sm md:text-base font-light text-text2 leading-relaxed whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }} />
      );
    }
  });

  flushList(lines.length);
  return elements;
}

function formatInline(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code class="bg-bg3 border border-border px-1.5 py-0.5 rounded font-mono text-xs text-accent">$1</code>')
    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="text-accent hover:underline">$1</a>');
}
