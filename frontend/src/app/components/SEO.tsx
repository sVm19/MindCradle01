import { useEffect } from 'react';

interface SEOProps {
  title: string;
  description: string;
  keywords?: string;
  canonical?: string;
  robots?: string;
  ogType?: string;
  ogImage?: string;
  schema?: Record<string, any> | Record<string, any>[];
}

export default function SEO({
  title,
  description,
  keywords,
  canonical,
  robots = 'index, follow',
  ogType = 'website',
  ogImage = 'https://mindcradle.online/mindcradle-logo.svg',
  schema,
}: SEOProps) {
  useEffect(() => {
    // 1. Title
    document.title = title;

    // 2. Core SEO tags
    updateMetaTag('description', description);
    if (keywords) {
      updateMetaTag('keywords', keywords);
    } else {
      removeMetaTag('keywords');
    }
    updateMetaTag('robots', robots);

    // 3. Canonical URL
    const canonicalUrl = canonical || window.location.href.split('?')[0];
    updateLinkTag('canonical', canonicalUrl);

    // 4. Open Graph (Facebook/Social Sharing)
    updateMetaProperty('og:title', title);
    updateMetaProperty('og:description', description);
    updateMetaProperty('og:url', canonicalUrl);
    updateMetaProperty('og:type', ogType);
    updateMetaProperty('og:image', ogImage);

    // 5. Twitter Cards
    updateMetaTag('twitter:title', title);
    updateMetaTag('twitter:description', description);
    updateMetaTag('twitter:image', ogImage);

    // 6. JSON-LD Schema
    if (schema) {
      injectJSONLD(schema);
    } else {
      removeJSONLD();
    }

    // Cleanup on unmount (or before next run)
    return () => {
      removeJSONLD();
    };
  }, [title, description, keywords, canonical, robots, ogType, ogImage, schema]);

  return null;
}

function updateMetaTag(name: string, content: string) {
  let el = document.querySelector(`meta[name="${name}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute('name', name);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

function removeMetaTag(name: string) {
  const el = document.querySelector(`meta[name="${name}"]`);
  if (el) {
    el.remove();
  }
}

function updateMetaProperty(property: string, content: string) {
  let el = document.querySelector(`meta[property="${property}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute('property', property);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

function updateLinkTag(rel: string, href: string) {
  let el = document.querySelector(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement('link');
    el.setAttribute('rel', rel);
    document.head.appendChild(el);
  }
  el.setAttribute('href', href);
}

function injectJSONLD(schema: any) {
  removeJSONLD();
  const script = document.createElement('script');
  script.setAttribute('type', 'application/ld+json');
  script.setAttribute('id', 'seo-jsonld');
  script.text = JSON.stringify(schema);
  document.head.appendChild(script);
}

function removeJSONLD() {
  const el = document.getElementById('seo-jsonld');
  if (el) {
    el.remove();
  }
}
