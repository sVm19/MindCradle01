import { useState } from 'react';

export default function Terms() {
  const todayDate = "June 28, 2026";

  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn">
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
          Terms of Service
        </h1>
        <p className="text-sm text-text3 mb-8 font-light">
          Last Updated: {todayDate}
        </p>

        {/* Table of Contents */}
        <nav className="mb-10 bg-bg border border-border rounded-2xl p-6">
          <h2 className="text-base font-bold text-text mb-3">Table of Contents</h2>
          <ul className="space-y-2 text-sm text-rose font-semibold">
            <li><a href="#agreement" className="hover:underline transition-all">1. Agreement</a></li>
            <li><a href="#license" className="hover:underline transition-all">2. Use License</a></li>
            <li><a href="#accounts" className="hover:underline transition-all">3. User Accounts</a></li>
            <li><a href="#conduct" className="hover:underline transition-all">4. Prohibited Conduct</a></li>
            <li><a href="#medical" className="hover:underline transition-all">5. Medical Disclaimer</a></li>
            <li><a href="#property" className="hover:underline transition-all">6. Intellectual Property</a></li>
            <li><a href="#liability" className="hover:underline transition-all">7. Liability Limitation</a></li>
            <li><a href="#indemnification" className="hover:underline transition-all">8. Indemnification</a></li>
            <li><a href="#termination" className="hover:underline transition-all">9. Termination</a></li>
            <li><a href="#changes" className="hover:underline transition-all">10. Changes to Terms</a></li>
            <li><a href="#governing" className="hover:underline transition-all">11. Governing Law</a></li>
            <li><a href="#contact" className="hover:underline transition-all">12. Contact</a></li>
          </ul>
        </nav>

        {/* Sections */}
        <div className="space-y-8 text-text2">
          
          <section id="agreement">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              1. AGREEMENT
            </h2>
            <p>
              By using MindCradle ("the Service"), <strong>you agree to be bound by these Terms of Service</strong>. If you disagree with any part of these terms, <strong>please do not use MindCradle</strong>.
            </p>
          </section>

          <section id="license">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              2. USE LICENSE
            </h2>
            <p>
              We grant you a personal, non-exclusive, non-transferable, and revocable license to use MindCradle under the following conditions:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li>You have a personal, non-commercial license to use MindCradle.</li>
              <li><strong>You may not:</strong> resell, redistribute, or use the Service for commercial purposes.</li>
              <li><strong>You may not:</strong> attempt to hack, reverse-engineer, or abuse the Service or its endpoints.</li>
            </ul>
          </section>

          <section id="accounts">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              3. USER ACCOUNTS
            </h2>
            <p>
              When creating an account, you accept the following duties:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li><strong>You are entirely responsible for protecting your login credentials</strong>.</li>
              <li><strong>You are responsible for all activity</strong> that occurs under your account.</li>
              <li>Keep your password confidential and do not share it with third parties.</li>
              <li>MindCradle is <strong>NOT liable for unauthorized access</strong> to your account resulting from your negligence.</li>
            </ul>
          </section>

          <section id="conduct">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              4. PROHIBITED CONDUCT
            </h2>
            <p>
              To maintain a supportive community environment, <strong>users may NOT:</strong>
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li>Share content that is illegal, hateful, abusive, harassing, or violates others' intellectual property rights.</li>
              <li>Spam, harass, or abuse other users or ARIA, our AI companion.</li>
              <li>Attempt to gain unauthorized access to other users' data or accounts.</li>
              <li>Disrupt or compromise the security and performance of the Service.</li>
            </ul>
          </section>

          <section id="medical">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              5. MEDICAL DISCLAIMER
            </h2>
            {/* Warning Callout Box */}
            <div className="bg-rose-dim border-l-4 border-rose rounded-r-xl p-5 my-4">
              <p className="text-sm font-semibold text-rose uppercase tracking-wide mb-1">
                ⚠️ Critical Safety Notice
              </p>
              <p className="text-text text-sm leading-relaxed">
                <strong>MindCradle is NOT a replacement for professional mental health care, medical diagnostics, or clinical therapy</strong>. 
                ARIA is an AI companion, not a licensed medical professional or therapist. If you are experiencing a mental health crisis, 
                please immediately contact emergency services (<strong>911 in US</strong>) or the suicide prevention lifeline (<strong>988</strong>).
              </p>
            </div>
          </section>

          <section id="property">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              6. INTELLECTUAL PROPERTY
            </h2>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li>All MindCradle content (including the UI, system designs, illustrations, brand assets, and code) remains our exclusive property.</li>
              <li><strong>Your data (mood logs, journals, and reflections) is YOUR property</strong>.</li>
              <li>You retain full rights to your data and <strong>can export and download your data anytime</strong>.</li>
            </ul>
          </section>

          <section id="liability">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              7. LIABILITY LIMITATION
            </h2>
            {/* Disclaimer Box */}
            <div className="bg-bg/40 border border-border/50 rounded-xl p-5 my-4">
              <p className="text-text text-sm">
                MindCradle is provided on an <strong>"as-is" and "as-available" basis</strong>. We make no warranties about:
              </p>
              <ul className="list-disc pl-5 mt-2 text-xs space-y-1 text-text3">
                <li>Uninterrupted or error-free operation of the Service.</li>
                <li>Correction of minor software bugs or temporary system offline times.</li>
                <li>Specific medical, clinical, or wellness outcomes from using MindCradle.</li>
              </ul>
              <p className="text-text text-sm mt-3">
                To the fullest extent allowed by applicable law, <strong>MindCradle shall NOT be liable for any indirect, incidental, special, or consequential damages</strong> arising from your use of the Service.
              </p>
            </div>
          </section>

          <section id="indemnification">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              8. INDEMNIFICATION
            </h2>
            <p>
              <strong>You agree to indemnify, defend, and hold harmless MindCradle</strong> and its officers from any claims, liabilities, or losses arising out of your misuse of the Service or violation of these Terms.
            </p>
          </section>

          <section id="termination">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              9. TERMINATION
            </h2>
            <ul className="list-disc pl-5 mt-2 space-y-2">
              <li>MindCradle may terminate or suspend your account <strong>without prior notice if you violate these Terms</strong>.</li>
              <li><strong>You can delete your account anytime</strong> directly from your Settings page.</li>
              <li>Upon account termination: <strong>You must export your data within 30 days</strong> before it is permanently and irreversibly purged from our database records.</li>
            </ul>
          </section>

          <section id="changes">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              10. CHANGES TO TERMS
            </h2>
            <p>
              We reserve the right to modify these Terms at any time. <strong>Your continued use of MindCradle constitutes acceptance of the updated Terms</strong>. We will notify you of major changes via your registered email address.
            </p>
          </section>

          <section id="governing">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              11. GOVERNING LAW
            </h2>
            <p>
              These Terms are governed by and construed in accordance with the laws of <strong>California, USA</strong>. Any legal disputes arising under these Terms shall be resolved in the courts located within <strong>San Francisco, California</strong>.
            </p>
          </section>

          <section id="contact">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              12. CONTACT
            </h2>
            <p>
              If you have any questions or concerns about these Terms, please contact us at: <a href="mailto:legal@mindcradle.online" className="text-rose font-semibold hover:underline">legal@mindcradle.online</a>.
            </p>
          </section>
        </div>

        {/* Footer */}
        <footer className="border-t border-border mt-12 pt-6 pb-2 text-sm text-text3 space-y-2">
          <div>Last Updated: {todayDate}</div>
          <div>
            <a href="mailto:legal@mindcradle.online" className="text-rose font-semibold hover:underline">
              Questions? Email us at legal@mindcradle.online
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}
