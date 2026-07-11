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
              MindCradle Premium offers a <strong>7-day free trial</strong> for new members. If you cancel your subscription before the trial period expires, <strong>you will not be charged</strong>.
            </p>
          </section>

          <section id="cancellation">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              2. Subscription Cancellation
            </h2>
            <p>
              You can cancel your monthly subscription at any time with one click from either the Settings or Pricing page. 
              Once canceled, your access remains active until the end of your current billing cycle, and <strong>no further charges will apply</strong>.
            </p>
          </section>

          <section id="eligibility">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              3. Refund Eligibility
            </h2>
            <div className="bg-bg/40 border border-border/50 rounded-xl p-5 my-4">
              <p className="text-text text-sm">
                We believe in complete transparency. You may request a full refund within <strong>14 days of payment</strong> under the following conditions:
              </p>
              <ul className="list-disc pl-5 mt-2 text-xs space-y-1 text-text3">
                <li>You experienced technical difficulties that prevented usage of Premium features.</li>
                <li>You forgot to cancel before the trial ended (applicable to initial charge only).</li>
                <li>You are dissatisfied with the service and wish to request a courtesy refund.</li>
              </ul>
            </div>
          </section>

          <section id="contact">
            <h2 className="text-[20px] font-bold text-text mb-3 mt-6">
              4. Contact Support
            </h2>
            <p>
              To request a refund, please email our support desk at: <a href="mailto:support@mindcradle.online" className="text-rose font-semibold hover:underline">support@mindcradle.online</a>.
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
