import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { ai as aiApi } from '@/lib/api';
import SEO from '@/app/components/SEO';
import { Search, BookOpen, Clock, Calendar, ArrowRight, User } from 'lucide-react';

interface BlogPostMeta {
  slug: string;
  title: string;
  summary: string;
  category: string;
  tags: string[];
  author: {
    name: string;
    avatar: string;
    bio: string;
  };
  published_at: string;
  image: string;
  read_time_mins: number;
}

export default function Blog() {
  const [posts, setPosts] = useState<BlogPostMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  useEffect(() => {
    aiApi.getBlogPosts()
      .then((data) => {
        setPosts(data);
      })
      .catch((err) => {
        console.error('Failed to load blog posts:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const categories = ['All', ...Array.from(new Set(posts.map((p) => p.category)))];

  const filteredPosts = posts.filter((post) => {
    const matchesSearch =
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCategory = selectedCategory === 'All' || post.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const blogSchema = {
    "@context": "https://schema.org",
    "@type": "Blog",
    "name": "MindCradle Wellness Blog",
    "description": "Insights, articles, and research on persistent AI memory, Knowledge Graphs, and relational wellness companions.",
    "publisher": {
      "@type": "Organization",
      "name": "MindCradle",
      "url": "https://mindcradle.online"
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12 space-y-12 animate-fadeIn text-left">
      <SEO
        title="Wellness Blog & AI Insights | MindCradle"
        description="Explore research and articles on persistent AI memory, long-term context, and digital wellness companions."
        schema={blogSchema}
      />

      {/* Breadcrumbs */}
      <nav className="text-xs text-text3 font-mono flex items-center gap-2">
        <Link to="/" className="hover:text-accent transition-colors">Home</Link>
        <span>/</span>
        <span className="text-text2">Blog</span>
      </nav>

      {/* Header */}
      <header className="space-y-4 max-w-2xl">
        <h1 className="font-[family-name:var(--font-serif)] text-3xl sm:text-4xl lg:text-5xl font-light text-text leading-tight">
          MindCradle Blog
        </h1>
        <p className="text-sm sm:text-base text-text3 font-light leading-relaxed">
          Exploring the future of human-AI relationship models, compounding context, and tools for digital mindfulness.
        </p>
      </header>

      {/* Filter and Search Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center border-b border-border pb-6">
        {/* Categories */}
        <div className="flex flex-wrap gap-2 w-full md:w-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-accent text-white shadow-lg shadow-accent/15'
                  : 'bg-bg2 border border-border text-text2 hover:border-border2 hover:text-text'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-80">
          <div className="absolute inset-y-0 left-3 flex items-center text-text3 pointer-events-none">
            <Search size={15} />
          </div>
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-bg2 border border-border rounded-xl pl-10 pr-4 py-2 text-xs text-text placeholder-text3 focus:outline-none focus:border-accent transition-all"
          />
        </div>
      </div>

      {/* Blog Cards Grid */}
      {loading ? (
        <div className="min-h-[30vh] flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        </div>
      ) : filteredPosts.length === 0 ? (
        <div className="text-center py-16 bg-bg2 border border-border rounded-3xl space-y-3">
          <BookOpen className="w-12 h-12 text-text3/40 mx-auto" />
          <h3 className="text-sm font-medium text-text">No articles found</h3>
          <p className="text-xs text-text3 max-w-xs mx-auto font-light">
            Try adjusting your search terms or selecting a different category.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {filteredPosts.map((post) => {
            const pubDate = new Date(post.published_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            });

            return (
              <article
                key={post.slug}
                className="bg-bg2 border border-border rounded-3xl overflow-hidden hover:border-accent/40 shadow-xl shadow-black/10 hover:shadow-accent/5 transition-all flex flex-col group"
              >
                {/* Featured Image */}
                <Link to={`/blog/${post.slug}`} className="block relative aspect-video overflow-hidden">
                  <img
                    src={post.image}
                    alt={post.title}
                    loading="lazy"
                    width="600"
                    height="337"
                    className="object-cover w-full h-full group-hover:scale-[1.03] transition-transform duration-500"
                  />
                  <div className="absolute top-4 left-4 bg-bg2/90 backdrop-blur-md px-3 py-1 rounded-full text-[10px] font-semibold text-accent border border-border font-mono">
                    {post.category}
                  </div>
                </Link>

                {/* Content */}
                <div className="p-6 sm:p-8 flex flex-col flex-1 space-y-4">
                  {/* Meta Row */}
                  <div className="flex items-center gap-4 text-[10.5px] text-text3 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock size={12} /> {post.read_time_mins} min read
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar size={12} /> {pubDate}
                    </span>
                  </div>

                  {/* Title & summary */}
                  <div className="space-y-2">
                    <h2 className="font-[family-name:var(--font-serif)] text-lg sm:text-xl font-light text-text leading-snug group-hover:text-accent transition-colors">
                      <Link to={`/blog/${post.slug}`}>{post.title}</Link>
                    </h2>
                    <p className="text-xs text-text3 font-light leading-relaxed">
                      {post.summary}
                    </p>
                  </div>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {post.tags.map((tag) => (
                      <span key={tag} className="text-[9px] bg-bg3 border border-border text-text3 px-2 py-0.5 rounded-full font-mono">
                        #{tag}
                      </span>
                    ))}
                  </div>

                  {/* Author & CTA Row */}
                  <div className="flex items-center justify-between pt-4 border-t border-border mt-auto">
                    {/* Author */}
                    <div className="flex items-center gap-2.5">
                      <img
                        src={post.author.avatar}
                        alt={post.author.name}
                        loading="lazy"
                        width="30"
                        height="30"
                        className="w-7 h-7 rounded-full object-cover border border-border"
                      />
                      <span className="text-xs text-text2 font-medium">
                        {post.author.name}
                      </span>
                    </div>

                    {/* Read CTA */}
                    <Link
                      to={`/blog/${post.slug}`}
                      className="text-xs font-semibold text-accent group-hover:text-accent2 flex items-center gap-1 transition-colors"
                    >
                      Read Article <ArrowRight size={13} className="group-hover:translate-x-0.5 transition-transform" />
                    </Link>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
