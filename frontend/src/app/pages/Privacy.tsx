import { useState } from 'react';
import SEO from '@/app/components/SEO';

export default function Privacy() {
  const todayDate = "June 28, 2026";

  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn">
      <SEO 
        title="Privacy Policy | MindCradle"
        description="Learn how MindCradle collects, stores, and protects your personal wellness data and journaling logs under GDPR and HIPAA privacy standards."
      />
      <div 
        className="w-full"
        style={{ 
          marginLeft: '2rem', 
          maxWidth: '800px',
          fontSize: '16px',
          lineHeight: '1.8'
        }}
      >
        <h1 className="font-[family-name:var(--font-serif)] text-3xl sm:text-4xl font-light mb-2 text-text">
          Privacy Policy
        </h1>
        <p className="text-sm text-text3 mb-8 font-light">
          Effective Date: {todayDate}
        </p>

        {/* Table of Contents */}
        <nav className="mb-10 bg-bg border border-border rounded-2xl p-6">
          <h2 className="text-base font-bold text-text mb-3">Table of Contents</h2>
          <ul className="space-y-2 text-sm text-rose font-semibold">
            <li><a href="#collection" className="hover:underline transition-all">Data Collection & Privacy First Approach</a></li>
            <li><a href="#usage" className="hover:underline transition-all">How We Use Your Data</a></li>
            <li><a href="#storage" className="hover:underline transition-all">Data Storage, Security, & GDPR Compliance</a></li>
            <li><a href="#ai" className="hover:underline transition-all">AI Integrations & Prompt Privacy</a></li>
            <li><a href="#crisis" className="hover:underline transition-all">Crisis Support & Safety Handover Policies</a></li>
            <li><a href="#rights" className="hover:underline transition-all">Your Rights (Right to erasure, access, portability)</a></li>
            <li><a href="#contact" className="hover:underline transition-all">Contact Us: privacy@mindcradle.online</a></li>
          </ul>
        </nav>

        {/* Sections */}
        <div className="space-y-8 text-text2">
          <section id="collection">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              Data Collection & Privacy First Approach
            </h2>
            <p>
              MindCradle is built on a privacy-first foundation. We gather minimal personal information required to run the core features of the dashboard. The information we collect includes:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li><strong>Account Credentials:</strong> Your email address, password, and chosen profile name are collected during user registration. These are securely processed and verified via Supabase authentication.</li>
              <li><strong>Daily Check-in Data:</strong> Numerical ratings of your state of calm (from 1 to 10), selected emotion categories, and custom narrative notes representing your state at check-in.</li>
              <li><strong>Routine Entries:</strong> Intentions, activity choices, completion timestamps, and reflection entries recorded during your morning and wind-down routines.</li>
              <li><strong>Journal Reflections:</strong> Text content you draft inside the digital journal tool, which is processed to generate personalized AI-driven reflections.</li>
              <li><strong>ARIA Chat Logs:</strong> Chat logs of all text exchanges with our AI companion, ARIA, to enable context retention, conversational memory, and consistency analysis.</li>
            </ul>
          </section>

          <section id="usage">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              How We Use Your Data
            </h2>
            <p>
              Your information is processed strictly to provide the tracking functionality and features. We do not sell or trade your data. The data is used to:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li>Synthesize calm indices and routine progress graphs on your dashboard.</li>
              <li>Maintain historical memory for ARIA to provide contextual, warm, and daily insights.</li>
              <li>Detect acute distress levels to proactively deliver helpful resources.</li>
              <li>Perform A/B experiments evaluating interface layouts to refine emotional reflection tracking.</li>
            </ul>
          </section>

          <section id="storage">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              Data Storage, Security, & GDPR Compliance
            </h2>
            <p>
              All connection states and transaction details are encrypted using Transport Layer Security (TLS) in transit, and databases are encrypted at rest. 
              If you are situated in the European Union (EU) or European Economic Area (EEA), you benefit from standard rights under the General Data Protection Regulation (GDPR). These rights include:
            </p>
          </section>

          <section id="ai">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              AI Integrations & Prompt Privacy
            </h2>
            <p>
              To power the reflective capabilities of ARIA, we utilize advanced language models.
              Before sending your messages or journal contents to these external AI models, all direct personally identifiable information (PII) is stripped out. AI providers do not use your conversations to train their public models, and all interactions are subject to strict data retention policies.
            </p>
          </section>

          <section id="crisis">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              Distress Support & Safety Handover Policies
            </h2>
            <p>
              ARIA is a conversational companion designed for positive self-awareness and daily reflection. ARIA is not a medical device, a replacement for professional clinical care, or an emergency responder.
              If you log severe or acute distress, our system will automatically show a support banner pointing to 24/7 hotlines (e.g. 988 Lifeline, Crisis Text Line). Furthermore, if you specify an emergency contact in settings, we may log a safety handover record to assist in notifying your designated supporter.
            </p>
          </section>

          <section id="rights">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              Your Rights (Right to erasure, access, portability)
            </h2>
            <p>
              Your user rights include the following capabilities which you can control directly from your account:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li><strong>Right of Erasure:</strong> The capability to completely purge your account and delete all associated journals, mood records, and chat history permanently.</li>
              <li><strong>Right to Restrict Processing:</strong> The ability to adjust notifications, disable background processing trackers, or disconnect push notification tokens.</li>
              <li><strong>Right to Access & Portability:</strong> The ability to request a complete export of all historical reflections linked to your identity.</li>
            </ul>
          </section>

          <section id="contact">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              Contact Us: privacy@mindcradle.online
            </h2>
            <p>
              If you have any questions about this Privacy Policy, your rights, or data handling, please contact us at: <a href="mailto:privacy@mindcradle.online" className="text-rose font-semibold hover:underline">privacy@mindcradle.online</a>.
            </p>
          </section>
        </div>

        {/* Footer */}
        <footer className="border-t border-border mt-12 pt-6 pb-2 text-sm text-text3 space-y-2">
          <div>Last updated: {todayDate}</div>
          <div>
            <a href="mailto:privacy@mindcradle.online" className="text-rose font-semibold hover:underline">
              Questions? Email us at privacy@mindcradle.online
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}
