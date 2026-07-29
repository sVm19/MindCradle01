import { useState } from 'react';
import SEO from '@/app/components/SEO';

export default function Refund() {
  const todayDate = "June 28, 2026";

  return (
    <div className="bg-bg2 text-text rounded-[28px] border border-border shadow-2xl p-8 sm:p-12 text-left animate-fadeIn">
      <SEO 
        title="Refund Policy | MindCradle"
        description="Review our subscription billing terms, trial period rules, and refund request guidelines."
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
          Refund Policy
        </h1>
        <p className="text-sm text-text3 mb-8 font-light">
          Last Updated: {todayDate}
        </p>

        {/* Table of Contents */}
        <nav className="mb-10 bg-bg border border-border rounded-2xl p-6">
          <h2 className="text-base font-bold text-text mb-3">Table of Contents</h2>
          <ul className="space-y-2 text-sm text-rose font-semibold">
            <li><a href="#trial" className="hover:underline transition-all">1. 7-Day Free Trial</a></li>
            <li><a href="#cancellation" className="hover:underline transition-all">2. Subscription Cancellation</a></li>
            <li><a href="#eligibility" className="hover:underline transition-all">3. Refund Eligibility</a></li>
            <li><a href="#contact" className="hover:underline transition-all">4. Contact Support</a></li>
          </ul>
        </nav>

        {/* Sections */}
        <div className="space-y-8 text-text2">
          
          <section id="trial">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              1. 7-Day Free Trial
            </h2>
            <p>
              MindCradle Premium offers a <strong>7-day free trial</strong> for new members to explore our full suite of tools, including unlimited ARIA AI companion interactions, historical mood data analysis, and private knowledge graph syncing. If you cancel your subscription at any point before the trial period expires, <strong>you will not be charged</strong>, and you will not incur any fees. This allows you to experience the complete benefits of Premium risk-free. Trial cancellations can be processed instantly through your user account dashboard.
            </p>
          </section>

          <section id="cancellation">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              2. Subscription Cancellation
            </h2>
            <p>
              You can cancel your monthly subscription at any time with one click from either the Settings or Pricing page. 
              Once canceled, your access remains active until the end of your current billing cycle, and <strong>no further charges will apply</strong>. We do not charge cancellation fees or impose hidden penalties. Please note that after cancellation, your subscription status will revert to the Free tier at the start of the next billing period, and your local data will remain cached according to our standard storage policies.
            </p>
          </section>

          <section id="eligibility">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              3. Refund Eligibility
            </h2>
            <div className="bg-bg/40 border border-border/50 rounded-xl p-5 my-4">
              <p className="text-text text-sm">
                We believe in complete billing transparency and want you to be fully satisfied with your purchase. You may request a full refund within <strong>14 days of any payment</strong> under the following conditions:
              </p>
              <ul className="list-disc pl-5 mt-2 text-xs space-y-1 text-text3">
                <li><strong>Technical Difficulties:</strong> You experienced bugs, connectivity issues, or backend outages that prevented you from using your Premium services.</li>
                <li><strong>Forgot to Cancel:</strong> You intended to cancel during the free trial but missed the deadline (applicable to the first subscription charge only).</li>
                <li><strong>Courtesies and Dissatisfaction:</strong> You are unhappy with the features or user experience and wish to request a courtesy refund.</li>
              </ul>
              <p className="text-text3 text-xs mt-3">
                Please note that refunds are processed through our primary merchant platform (Stripe/Creem) and typically take between <strong>5 to 10 business days</strong> to appear on your bank statement.
              </p>
            </div>
          </section>

          <section id="contact">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              4. Contact Support
            </h2>
            <p>
              To submit a refund request or clarify billing questions, please contact our support desk directly via email at: <a href="mailto:support@mindcradle.online" className="text-rose font-semibold hover:underline">support@mindcradle.online</a>. Please include the email address associated with your user account and your transaction ID (found in your email receipt) to ensure a prompt resolution. Our customer care team responds to all billing inquiries within 24 to 48 hours.
            </p>
          </section>
        </div>

        {/* Footer */}
        <footer className="border-t border-border mt-12 pt-6 pb-2 text-sm text-text3 space-y-2">
          <div>Last Updated: {todayDate}</div>
          <div>
            <a href="mailto:support@mindcradle.online" className="text-rose font-semibold hover:underline">
              Questions? Email us at support@mindcradle.online
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}
