import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { ai as aiApi } from '@/lib/api';
import SEO from '@/app/components/SEO';
import { Search, BookOpen, ChevronRight, FileText, Menu, X } from 'lucide-react';

interface DocMeta {
  slug: string;
  title: string;
  category: string;
  order: number;
}

interface DocPage {
  slug: string;
  title: string;
  category: string;
  order: number;
  content: string;
  modified_at: string;
}

export default function Docs() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const activeSlug = slug || 'introduction';

  const [docList, setDocList] = useState<DocMeta[]>([]);
  const [activeDoc, setActiveDoc] = useState<DocPage | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Load sidebar document index on mount
  useEffect(() => {
    aiApi.getDocs()
      .then((data) => {
        setDocList(data.sort((a, b) => a.order - b.order));
      })
      .catch((err) => {
        console.error('Failed to load documentation index:', err);
      })
      .finally(() => {
        setLoadingList(false);
      });
  }, []);

  // Load active document on slug change
  useEffect(() => {
    setLoadingDoc(true);
    aiApi.getDocBySlug(activeSlug)
      .then((data) => {
        setActiveDoc(data);
      })
      .catch((err) => {
        console.error('Failed to load document content:', err);
        setActiveDoc(null);
      })
      .finally(() => {
        setLoadingDoc(false);
        setSidebarOpen(false); // close sidebar on mobile
      });
  }, [activeSlug]);

  // Client-side text filter on sidebar links
  const filteredDocs = docList.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group sidebar documents by category
  const docsByCategory: { [category: string]: DocMeta[] } = {};
  filteredDocs.forEach((doc) => {
    if (!docsByCategory[doc.category]) {
      docsByCategory[doc.category] = [];
    }
    docsByCategory[doc.category].push(doc);
  });

  // Intercept inner article links to prevent full page reloads, keeping SPA routing
  const handleContentClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    const anchor = target.closest('a');
    if (anchor) {
      const href = anchor.getAttribute('href');
      if (href && href.startsWith('/docs')) {
        e.preventDefault();
        navigate(href);
      }
    }
  };

  // Structured Data schemas
  const docSchema = activeDoc ? {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": activeDoc.title,
    "description": `Read the documentation for MindCradle - ${activeDoc.title}.`,
    "dateModified": activeDoc.modified_at,
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
      "@id": `https://mindcradle.online/docs/${activeDoc.slug}`
    }
  } : undefined;

  const breadcrumbsSchema = activeDoc ? {
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
        "name": "Docs",
        "item": "https://mindcradle.online/docs"
      },
      {
        "@type": "ListItem",
        "position": 3,
        "name": activeDoc.title,
        "item": `https://mindcradle.online/docs/${activeDoc.slug}`
      }
    ]
  } : undefined;

  const seoTitle = activeDoc ? `${activeDoc.title} | MindCradle Docs` : 'Documentation | MindCradle';
  const seoDesc = activeDoc ? `Explore MindCradle support guides and developer references for ${activeDoc.title}.` : 'Search guides and references for the MindCradle wellness companion.';

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:py-10 text-left relative min-h-[70vh]">
      {activeDoc && (
        <SEO
          title={seoTitle}
          description={seoDesc}
          schema={docSchema && breadcrumbsSchema ? [docSchema, breadcrumbsSchema] : undefined}
        />
      )}

      {/* Mobile Sidebar Toggle Header */}
      <div className="lg:hidden flex items-center justify-between bg-bg2 border border-border p-3 rounded-2xl mb-6">
        <button
          onClick={() => setSidebarOpen(true)}
          className="flex items-center gap-2 text-xs font-semibold text-text hover:text-accent transition-colors cursor-pointer"
        >
          <Menu size={16} /> Browse Docs
        </button>
        <span className="text-xs text-text3 font-mono">
          {activeDoc?.title}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* ── Sidebar Navigation Column (Spans 1 col) ── */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 bg-bg2 border-r border-border p-6 transform transition-transform duration-300 lg:static lg:w-auto lg:border-r-0 lg:p-0 lg:transform-none lg:z-0 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          }`}
        >
          <div className="flex flex-col h-full space-y-6">
            {/* Mobile Close Button */}
            <div className="lg:hidden flex justify-between items-center pb-2 border-b border-border">
              <span className="font-[family-name:var(--font-serif)] text-sm font-semibold text-text">Browse Documentation</span>
              <button onClick={() => setSidebarOpen(false)} className="text-text3 hover:text-text cursor-pointer">
                <X size={18} />
              </button>
            </div>

            {/* Docs Title */}
            <div className="hidden lg:block">
              <h2 className="font-[family-name:var(--font-serif)] text-lg font-light text-text flex items-center gap-2">
                <BookOpen size={16} className="text-accent" /> Documentation
              </h2>
            </div>

            {/* Search Input */}
            <div className="relative">
              <div className="absolute inset-y-0 left-3 flex items-center text-text3 pointer-events-none">
                <Search size={14} />
              </div>
              <input
                type="text"
                placeholder="Search docs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-bg3 border border-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-text placeholder-text3 focus:outline-none focus:border-accent transition-all"
              />
            </div>

            {/* Grouped Sidebar List */}
            {loadingList ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
              </div>
            ) : Object.keys(docsByCategory).length === 0 ? (
              <div className="text-xs text-text3 italic py-4">No matching docs found.</div>
            ) : (
              <div className="space-y-6 overflow-y-auto pr-1 flex-1">
                {Object.keys(docsByCategory).map((catName) => (
                  <div key={catName} className="space-y-2">
                    <h3 className="text-[10px] text-text3 uppercase tracking-[0.15em] font-bold font-mono">
                      {catName}
                    </h3>
                    <ul className="space-y-1">
                      {docsByCategory[catName].map((doc) => {
                        const isCurrent = activeSlug === doc.slug;
                        return (
                          <li key={doc.slug}>
                            <Link
                              to={`/docs/${doc.slug}`}
                              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all ${
                                isCurrent
                                  ? 'bg-accent/10 border border-accent/20 text-accent font-medium'
                                  : 'text-text2 hover:bg-bg3 border border-transparent'
                              }`}
                            >
                              <FileText size={13} />
                              <span className="truncate">{doc.title}</span>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* Mobile Sidebar Overlay Backdrop */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 lg:hidden"
          />
        )}

        {/* ── Content Viewer Column (Spans 3 cols) ── */}
        <div className="lg:col-span-3 space-y-6 lg:pl-6 border-l border-border/10">
          {/* Breadcrumbs */}
          {activeDoc && (
            <nav className="text-xs text-text3 font-mono flex flex-wrap items-center gap-2">
              <Link to="/" className="hover:text-accent transition-colors">Home</Link>
              <span>/</span>
              <span className="hover:text-accent cursor-pointer" onClick={() => navigate('/docs/introduction')}>Docs</span>
              <span>/</span>
              <span className="text-text3/75">{activeDoc.category}</span>
              <span>/</span>
              <span className="text-text2 truncate max-w-xs">{activeDoc.title}</span>
            </nav>
          )}

          {/* Doc body */}
          {loadingDoc ? (
            <div className="min-h-[40vh] flex items-center justify-center">
              <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
            </div>
          ) : !activeDoc ? (
            <div className="text-center py-16 bg-bg2 border border-border rounded-3xl space-y-3">
              <FileText className="w-12 h-12 text-text3/40 mx-auto" />
              <h3 className="text-sm font-medium text-text">Page Not Found</h3>
              <p className="text-xs text-text3 max-w-xs mx-auto font-light">
                The documentation page you requested does not exist.
              </p>
            </div>
          ) : (
            <article
              onClick={handleContentClick}
              className="prose prose-invert max-w-none font-sans bg-bg2/40 border border-border/80 rounded-3xl p-6 sm:p-10 shadow-2xl relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(20,184,166,0.03),transparent_40%)] pointer-events-none" />
              <div className="relative z-10">
                {renderMarkdown(activeDoc.content)}
              </div>
            </article>
          )}
        </div>
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
        <ul key={`list-${key}`} className="list-disc pl-5 mb-5 text-xs sm:text-sm md:text-base space-y-2 font-light text-text2 leading-relaxed">
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
      elements.push(<h1 key={index} className="text-2xl sm:text-3xl md:text-4xl font-[family-name:var(--font-serif)] font-light text-text mt-4 mb-4 border-b border-border pb-2.5 flex items-center gap-2">{trimmed.substring(2)}</h1>);
    } else if (trimmed.startsWith('## ')) {
      elements.push(<h2 key={index} className="text-xl sm:text-2xl font-[family-name:var(--font-serif)] font-light text-text mt-8 mb-4 border-l-2 border-accent pl-3.5">{trimmed.substring(3)}</h2>);
    } else if (trimmed.startsWith('### ')) {
      elements.push(<h3 key={index} className="text-lg sm:text-xl font-semibold text-text mt-6 mb-3">{trimmed.substring(4)}</h3>);
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
