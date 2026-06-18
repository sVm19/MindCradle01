import { useNavigate } from 'react-router';
import { useAuth, getInitials } from '@/lib/auth';
import { sanitizeForInput } from '@/lib/sanitize';
import { useState, useEffect } from 'react';
import { profile as profileApi, auth as authApi } from '@/lib/api';
import { Lock, Settings as SettingsIcon, CheckCircle, Clock, ShieldAlert, Eye, Download, AlertTriangle, X } from 'lucide-react';
import GuestGate from '@/app/components/GuestGate';

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initials = user ? getInitials(user.name || user.email) : '?';

  const [emergencyContact, setEmergencyContact] = useState('');
  const [notifyOnCrisis, setNotifyOnCrisis] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const [ageVerified, setAgeVerified] = useState(false);
  const [ageVerifiedAt, setAgeVerifiedAt] = useState<string | null>(null);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [privacyAcceptedAt, setPrivacyAcceptedAt] = useState<string | null>(null);

  const [isPolicyOpen, setIsPolicyOpen] = useState(false);
  const [isWithdrawOpen, setIsWithdrawOpen] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!user) return;
    profileApi.get()
      .then((res) => {
        setEmergencyContact(res.emergency_contact || '');
        setNotifyOnCrisis(res.notify_on_crisis || false);
      })
      .catch((err) => {
        if (import.meta.env.DEV) {
          console.error('Failed to load profile:', err);
        }
      });

    // Fetch age verification from DB
    authApi.checkAgeVerified()
      .then((res) => {
        setAgeVerified(res.age_verified);
        setAgeVerifiedAt(res.verified_at);
      })
      .catch(() => {});

    // Fetch privacy acceptance from DB, fallback to localStorage
    authApi.checkPrivacy()
      .then((res) => {
        setPrivacyAccepted(res.privacy_accepted);
        setPrivacyAcceptedAt(res.accepted_at);
      })
      .catch(() => {
        const localPrivacy = localStorage.getItem('privacy_accepted') === 'true';
        setPrivacyAccepted(localPrivacy);
        
        const localPrivacyData = localStorage.getItem('privacy_accepted_data');
        if (localPrivacyData) {
          try {
            const parsed = JSON.parse(localPrivacyData);
            setPrivacyAcceptedAt(parsed.accepted_at);
          } catch {
            setPrivacyAcceptedAt(null);
          }
        }
      });
  }, [user]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    try {
      await profileApi.update({
        emergency_contact: emergencyContact,
        notify_on_crisis: notifyOnCrisis,
      });
      setSaveStatus('Saved successfully ✓');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error(err);
      }
      setSaveStatus('Failed to save settings.');
      setTimeout(() => setSaveStatus(null), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadPDF = () => {
    const pdfContent = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 500 >>
stream
BT
/F1 14 Tf
72 720 Td
(MindCradle Privacy Policy) Tj
/F1 10 Tf
0 -20 Td
(Effective Date: June 17, 2026) Tj
0 -30 Td
(This document summarizes the privacy policies and terms of service for MindCradle.) Tj
0 -20 Td
(1. Data Collection & Privacy First Approach:) Tj
0 -12 Td
(   We gather minimal account details, mood entries, ritual logs, and journal reflections.) Tj
0 -20 Td
(2. Data Usage & AI Companion Context:) Tj
0 -12 Td
(   Data is processed strictly to visualize wellness scores and facilitate natural conversations.) Tj
0 -20 Td
(3. Storage & Retention Policies:) Tj
0 -12 Td
(   All credentials and session databases are encrypted in transit and at rest in Supabase.) Tj
0 -20 Td
(4. Crisis Support & Safety Handovers:) Tj
0 -12 Td
(   Acute distress triggers automated crisis resources and alerts your emergency contact.) Tj
0 -30 Td
(For complete terms and detailed legal guidelines, please refer to the digital copy) Tj
0 -12 Td
(available at your account dashboard under Settings > Privacy & Legal.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000232 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
782
%%EOF`;

    const blob = new Blob([pdfContent], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'MindCradle_Privacy_Policy.pdf';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleWithdrawConsent = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeleteError('');
    setIsDeleting(true);

    if (!user) return;

    try {
      await authApi.withdrawConsent(confirmPassword);
      
      // Clear local storage
      localStorage.removeItem('privacy_accepted');
      localStorage.removeItem('privacy_accepted_data');
      localStorage.removeItem('age_verified');
      
      logout();
      setIsWithdrawOpen(false);
      setConfirmPassword('');
      navigate('/');
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Account deletion failed. Please verify your password.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!user) {
    return (
      <GuestGate
        title="Account Settings"
        description="Manage your profile. Setup crisis contact preferences, configure security rules, and view badge milestones."
        icon={<SettingsIcon className="w-8 h-8 text-accent" />}
      />
    );
  }

  return (
    <>
      <div className="space-y-8 animate-fadeIn text-left">
      {/* Header */}
      <div>
        <div className="text-xs text-accent tracking-[0.1em] uppercase mb-4">ACCOUNT</div>
        <h1 className="text-3xl font-light text-text mb-2">Settings</h1>
      </div>

      {/* Profile Card */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-6">
        <div className="text-xs text-text3 uppercase tracking-wider mb-5">Profile</div>
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent2 to-teal flex items-center justify-center text-xl font-medium text-white flex-shrink-0">
            {initials}
          </div>
          <div>
            <div className="text-base font-medium text-text">{user?.name || '—'}</div>
            <div className="text-sm text-text3 mt-0.5">{user?.email}</div>
          </div>
        </div>
      </section>

      {/* Safety Settings */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-6 space-y-4">
        <div className="text-xs text-accent uppercase tracking-wider mb-2">Safety & Emergency Contact</div>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="emergency-contact" className="text-xs text-text2 font-medium">
              Emergency Contact (Email, Phone, or Name)
            </label>
            <input
              id="emergency-contact"
              type="text"
              value={emergencyContact}
              onChange={(e) => setEmergencyContact(sanitizeForInput(e.target.value))}
              placeholder="e.g. Spouse (+1-555-0100) or contact@domain.com"
              className="w-full bg-bg3 border border-border rounded-[10px] px-4 py-2.5 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-accent"
            />
          </div>
          <div className="flex items-start gap-3 pt-2">
            <input
              id="notify-on-crisis"
              type="checkbox"
              checked={notifyOnCrisis}
              onChange={(e) => setNotifyOnCrisis(e.target.checked)}
              className="w-4 h-4 rounded border-border text-accent bg-bg3 mt-0.5 focus:ring-0 focus:ring-offset-0 cursor-pointer"
            />
            <div className="space-y-1">
              <label htmlFor="notify-on-crisis" className="text-xs text-text font-medium cursor-pointer">
                Notify emergency contact if crisis detected
              </label>
              <p className="text-[10px] text-text3">
                If active self-harm or suicidal intent is detected, we will attempt to send an automated alert to your emergency contact.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4 pt-2">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2.5 bg-accent hover:bg-accent2 text-white rounded-[10px] text-sm font-medium transition-all disabled:opacity-50 cursor-pointer"
            >
              {isSaving ? 'Saving...' : 'Save Safety Settings'}
            </button>
            {saveStatus && (
              <span className={`text-xs ${saveStatus.includes('failed') ? 'text-rose' : 'text-teal'} font-medium`}>
                {saveStatus}
              </span>
            )}
          </div>
        </div>
      </section>

      {/* App Info */}
      <section className="bg-bg2 border border-border rounded-[20px] px-6 py-6 space-y-4">
        <div className="text-xs text-text3 uppercase tracking-wider mb-2">About</div>
        {[
          { label: 'App', value: 'MindCradle' },
          { label: 'Version', value: '0.1.0' },
          { label: 'Backend', value: 'FastAPI + PocketBase' },
          { label: 'AI Companion', value: 'ARIA (Gemma · OpenRouter)' },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <span className="text-text3">{label}</span>
            <span className="text-text">{value}</span>
          </div>
        ))}
      </section>

      {/* Privacy Note */}
      <section className="bg-bg3/60 border border-border rounded-[14px] px-5 py-4">
        <div className="flex gap-3">
          <div className="text-lg">🔒</div>
          <div>
            <div className="text-sm text-text mb-1">Your data is private</div>
            <div className="text-xs text-text2">
              All journal entries, mood logs, and conversations are stored securely and are only visible to you. ARIA conversations are context-aware but not shared with third parties.
            </div>
          </div>
        </div>
      </section>

      {/* Privacy & Legal Section */}
      <section className="space-y-4 text-left">
        <div className="text-xs text-accent tracking-[0.1em] uppercase">Privacy & Legal</div>
        
        <div 
          className="rounded-[20px] p-6 space-y-5"
          style={{
            background: 'var(--color-background-secondary, rgba(255, 255, 255, 0.05))',
            border: '0.5px solid var(--color-border-tertiary, rgba(255, 255, 255, 0.08))',
            backdropFilter: 'blur(16px)',
          }}
        >
          <div className="text-sm font-semibold text-text uppercase tracking-wider">Your Privacy</div>
          
          <div className="space-y-3.5">
            {/* Privacy Policy Accepted Info */}
            <div className="flex items-start justify-between gap-4 text-sm">
              <div className="space-y-1">
                <div className="text-text2 font-medium flex items-center gap-1.5">
                  <CheckCircle size={15} className={privacyAccepted ? 'text-green' : 'text-text3'} />
                  <span>Privacy Policy Acceptance</span>
                </div>
                <div className="text-xs text-text3 flex items-center gap-1">
                  <Clock size={12} />
                  <span>{privacyAcceptedAt ? `Accepted on ${new Date(privacyAcceptedAt).toLocaleDateString()}` : 'Not accepted'}</span>
                </div>
              </div>
              <span className={`text-xs font-semibold uppercase tracking-wider ${privacyAccepted ? 'text-green' : 'text-text3'}`}>
                {privacyAccepted ? 'Accepted' : 'Not accepted'}
              </span>
            </div>

            {/* Age Verification Info */}
            <div className="flex items-start justify-between gap-4 text-sm pt-2 border-t border-border/40">
              <div className="space-y-1">
                <div className="text-text2 font-medium flex items-center gap-1.5">
                  <CheckCircle size={15} className={ageVerified ? 'text-green' : 'text-text3'} />
                  <span>Age Verification State</span>
                </div>
                <div className="text-xs text-text3 flex items-center gap-1">
                  <Clock size={12} />
                  <span>{ageVerifiedAt ? `Verified on ${new Date(ageVerifiedAt).toLocaleDateString()}` : 'Not verified'}</span>
                </div>
              </div>
              <span className={`text-xs font-semibold uppercase tracking-wider ${ageVerified ? 'text-green' : 'text-text3'}`}>
                {ageVerified ? 'Verified (18+)' : 'Not verified'}
              </span>
            </div>

            {/* Data Collection summary */}
            <div className="flex items-start gap-3 bg-bg3/30 border border-border/40 rounded-xl p-3.5 text-xs text-text2 leading-relaxed">
              <ShieldAlert size={16} className="text-accent flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-text">Data Collection Summary:</span> We collect mood logs, morning/evening rituals, journal logs, and chat logs with ARIA. We use this data to calculate calm scores, analyze recovery trends, and maintain custom conversational context for ARIA's reflections.
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              onClick={() => setIsPolicyOpen(true)}
              className="flex-1 py-2.5 bg-bg3 hover:bg-bg4 border border-border text-text2 hover:text-text rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            >
              <Eye size={14} />
              <span>View Full Privacy Policy</span>
            </button>

            <button
              onClick={handleDownloadPDF}
              className="flex-1 py-2.5 bg-bg3 hover:bg-bg4 border border-border text-text2 hover:text-text rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            >
              <Download size={14} />
              <span>Download Privacy Policy</span>
            </button>

            <button
              onClick={() => {
                setDeleteError('');
                setConfirmPassword('');
                setIsWithdrawOpen(true);
              }}
              className="flex-1 py-2.5 bg-rose/10 border border-rose/30 text-rose hover:bg-rose/20 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            >
              <AlertTriangle size={14} />
              <span>Withdraw Consent</span>
            </button>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-bg2 border border-rose/20 rounded-[20px] px-6 py-6">
        <div className="text-xs text-rose/70 uppercase tracking-wider mb-4">Account</div>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-text font-medium">Sign out</div>
            <div className="text-xs text-text3 mt-0.5">You'll need to sign in again to access your data.</div>
          </div>
          <button
            onClick={handleLogout}
            className="px-5 py-2.5 bg-rose/10 border border-rose/30 text-rose rounded-[10px] text-sm font-medium hover:bg-rose/20 transition-all cursor-pointer"
          >
            Sign out
          </button>
        </div>
      </section>
    </div>

    {/* Read-Only Privacy Policy Modal */}
    {isPolicyOpen && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-fadeIn">
        <div className="w-full max-w-2xl bg-bg2 border border-border rounded-[24px] p-6 md:p-8 relative shadow-2xl animate-slideIn flex flex-col max-h-[90vh] text-left">
          <button
            onClick={() => setIsPolicyOpen(false)}
            className="absolute top-5 right-5 text-text3 hover:text-text cursor-pointer transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>

          <h1 className="text-xl md:text-2xl font-light text-text mb-4 font-[family-name:var(--font-serif)]">
            Privacy Policy & Terms
          </h1>

          <div
            className="flex-1 overflow-y-auto pr-3 mb-4 h-[400px] border border-border/50 rounded-xl bg-bg3/20 p-4 text-xs md:text-[13px] text-text3 leading-relaxed space-y-4 select-text"
            style={{ scrollbarWidth: 'thin' }}
          >
            <p className="font-semibold text-text">Effective Date: June 17, 2026</p>
            <p>
              Welcome to MindCradle. Your trust is our most valuable asset. We are dedicated to providing a safe, secure, and supportive environment for your wellness journey. This Privacy Policy details how we handle, protect, and process your data. Please read this document in its entirety to understand how we store and handle your personal logs, mood entries, and conversation details with ARIA, our built-in wellness AI assistant.
            </p>
            <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
              1. Data Collection & Privacy First Approach
            </h2>
            <p>
              MindCradle is built on a privacy-first foundation. We gather minimal personal information required to run the core features of the mental health dashboard. The information we collect includes:
            </p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li>
                <strong>Account Credentials:</strong> Your email address, password, and chosen profile name are collected during user registration. These are securely processed and verified via Supabase authentication.
              </li>
              <li>
                <strong>Mood Logging Data:</strong> Numerical ratings of your state of calm (from 1 to 10), selected emotion categories, and custom narrative notes representing your state at check-in.
              </li>
              <li>
                <strong>Ritual Entries:</strong> Intentions, activity choices, completion timestamps, and reflection entries recorded during your morning and wind-down routines.
              </li>
              <li>
                <strong>Journal Reflections:</strong> Text content you draft inside the digital journal tool, which is processed to generate personalized AI-driven reflections.
              </li>
              <li>
                <strong>ARIA Chat Logs:</strong> Chat logs of all text exchanges with our AI companion, ARIA, to enable context retention, conversational memory, and distress level analysis.
              </li>
            </ul>
            <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
              2. How We Use Your Data
            </h2>
            <p>
              Your information is processed strictly to provide the mental wellness tracking functionality and features. We do not sell or trade your data. The data is used to:
            </p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li>Synthesize recovery rates, calm indices, and wellness progress graphs on your dashboard.</li>
              <li>Maintain historical memory for ARIA to provide contextual, warm, and highly personalized daily insights.</li>
              <li>Detect acute distress levels or potential crises to proactively deliver emergency resources.</li>
              <li>Perform internal A/B experiments to evaluate feature engagement, response speeds, and UI layouts to continuously refine the mental health tools.</li>
            </ul>
            <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
              3. Data Storage, Security, & GDPR Compliance
            </h2>
            <p>
              All connection states and transaction details are encrypted using Transport Layer Security (TLS) in transit, and databases are encrypted at rest.
            </p>
            <p>
              If you are situated in the European Union (EU) or European Economic Area (EEA), you benefit from standard rights under the General Data Protection Regulation (GDPR). These rights include:
            </p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li><strong>Right of Erasure:</strong> The capability to completely purge your account and delete all associated journals, mood records, and chat history permanently.</li>
              <li><strong>Right to Restrict Processing:</strong> The ability to adjust notifications, disable background processing trackers, or disconnect push notification tokens.</li>
              <li><strong>Right to Access & Portability:</strong> The ability to request a complete export of all historical wellness data linked to your identity.</li>
            </ul>
            <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
              4. AI Integrations & Prompt Privacy
            </h2>
            <p>
              To power the reflective capabilities of ARIA, we utilize advanced language models via secure APIs (such as OpenRouter).
            </p>
            <p>
              Before sending your messages or journal contents to these external AI models, all direct personally identifiable information (PII) is stripped out. AI providers do not use your conversations to train their public models, and all interactions are subject to strict data retention policies.
            </p>
            <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
              5. Crisis Support & Safety Handover Policies
            </h2>
            <p>
              ARIA is a wellness assistant designed for positive emotional tracking and support. ARIA is not a medical device, a replacement for professional clinical therapy, or an emergency responder.
            </p>
            <p>
              If you log severe or acute distress, our system will automatically show a crisis banner pointing to 24/7 hotlines (e.g. 988 Lifeline, Crisis Text Line). Furthermore, if you specify an emergency contact in settings, we may log a safety handover record to assist in notifying your designated supporter.
            </p>
            <h2 className="text-sm font-semibold text-text pt-2 border-b border-border/20 pb-1 uppercase tracking-wider">
              6. Consent and Agreement
            </h2>
            <p>
              By checking the consent checkbox and registering, you confirm that you are at least 18 years of age, understand ARIA is an AI companion, and agree to our data collection, processing, and crisis management policies.
            </p>
          </div>

          <div className="flex justify-end pt-2 border-t border-border">
            <button
              type="button"
              onClick={() => setIsPolicyOpen(false)}
              className="px-6 py-2 bg-accent text-white rounded-xl text-xs font-semibold hover:opacity-90 transition-all cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )}

    {/* Withdraw Consent Confirmation Modal */}
    {isWithdrawOpen && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fadeIn">
        <div className="w-full max-w-md bg-bg2 border border-rose/20 rounded-[24px] p-6 relative shadow-2xl animate-slideIn text-left space-y-5">
          <button
            onClick={() => setIsWithdrawOpen(false)}
            className="absolute top-5 right-5 text-text3 hover:text-text cursor-pointer transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>

          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border pb-3">
            <div className="w-10 h-10 rounded-full bg-rose/15 flex items-center justify-center text-rose">
              <AlertTriangle size={22} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-text">Withdraw Consent</h2>
              <p className="text-xs text-text3">Danger Zone Action</p>
            </div>
          </div>

          {/* Warning Message */}
          <div className="bg-rose/10 border border-rose/30 text-rose text-xs rounded-xl p-3 flex items-start gap-2 leading-relaxed">
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
            <span><strong>Warning:</strong> This will delete your account and all data. This action is permanent, non-reversible, and will immediately wipe your logs, rituals, journal entries, and ARIA chats.</span>
          </div>

          {deleteError && (
            <div className="bg-rose/10 border border-rose/30 text-rose text-xs rounded-lg px-3 py-2 animate-fadeIn">
              {deleteError}
            </div>
          )}

          {/* Password input */}
          <form onSubmit={handleWithdrawConsent} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs text-text2 font-medium">Confirm Password</label>
              <input
                type="password"
                required
                placeholder="Enter password to confirm deletion"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-bg3 border border-border rounded-xl px-4 py-2.5 text-xs text-text placeholder:text-text3 focus:outline-none focus:border-rose/40 transition-colors"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={isDeleting || !confirmPassword}
                className="flex-1 py-2.5 bg-rose text-white rounded-xl text-xs font-semibold hover:opacity-90 transition-all disabled:opacity-50 flex justify-center items-center cursor-pointer"
              >
                {isDeleting ? 'Deleting Account...' : 'Delete Account & Data'}
              </button>
              <button
                type="button"
                onClick={() => setIsWithdrawOpen(false)}
                className="px-5 py-2.5 bg-bg3 border border-border text-text2 hover:text-text rounded-xl text-xs font-medium hover:bg-bg4 transition-all cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    )}
  </>
  );
}
