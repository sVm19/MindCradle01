import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@/lib/auth';
import { 
  growth as growthApi, 
  ExperimentAnalytics, 
  FunnelStepAnalytics 
} from '@/lib/api';
import { 
  ArrowLeft, 
  TrendingUp, 
  Activity, 
  CheckCircle2, 
  HelpCircle,
  Play,
  Pause,
  Plus,
  RefreshCw,
  Info,
  Sparkles
} from 'lucide-react';
import GuestGate from '@/app/components/GuestGate';

export default function GrowthDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [experiments, setExperiments] = useState<ExperimentAnalytics[]>([]);
  const [funnel, setFunnel] = useState<FunnelStepAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  // Form for creating new experiments
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newExpName, setNewExpName] = useState('');
  const [newExpDesc, setNewExpDesc] = useState('');
  const [newExpVariants, setNewExpVariants] = useState('control, treatment');
  const [creating, setCreating] = useState(false);

  const fetchAnalytics = async (silent = false) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const stats = await growthApi.getStats();
      if (stats) {
        setExperiments(stats.experiments || []);
        setFunnel(stats.funnel || []);
      }
    } catch (err) {
      console.error('Failed to load growth analytics:', err);
      setError('Failed to load product analytics data. Please ensure database migrations are fully set up.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchAnalytics();
    }
  }, [user]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAnalytics(true);
  };

  const handleStatusToggle = async (id: string, currentStatus: string) => {
    const nextStatus = currentStatus === 'running' ? 'paused' : 'running';
    try {
      await growthApi.updateExperimentStatus(id, nextStatus);
      // Reload stats
      fetchAnalytics(true);
    } catch (err) {
      alert('Failed to update experiment status');
    }
  };

  const handleCreateExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newExpName || !newExpDesc) return;

    setCreating(true);
    try {
      const variantsList = newExpVariants
        .split(',')
        .map(v => v.trim())
        .filter(v => v.length > 0);

      await growthApi.createExperiment(newExpName, newExpDesc, variantsList);
      setShowCreateModal(false);
      setNewExpName('');
      setNewExpDesc('');
      setNewExpVariants('control, treatment');
      fetchAnalytics(true);
    } catch (err) {
      alert('Failed to register experiment. Ensure the name is unique.');
    } finally {
      setCreating(false);
    }
  };

  if (!user) {
    return (
      <GuestGate
        title="Admin Growth Analytics"
        description="View activation funnel data and manage active A/B experiments."
        icon={<Activity className="w-8 h-8 text-accent animate-pulse" />}
      />
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-10 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/settings')}
            className="p-2 text-text3 hover:text-text hover:bg-bg2 rounded-full transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-light text-text">Product Growth Console</h1>
            <p className="text-sm text-text2">Measure activation funnels, evaluate statistical significance, and configure experiments.</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2.5 bg-bg2 border border-border hover:border-border2 text-text rounded-full transition-all flex items-center justify-center disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2.5 bg-accent hover:bg-accent2 text-white rounded-full font-medium text-xs transition-all flex items-center gap-2 shadow-md"
          >
            <Plus className="w-4 h-4" /> New A/B Test
          </button>
        </div>
      </div>

      {loading ? (
        <div className="min-h-[50vh] flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        </div>
      ) : error ? (
        <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-[20px] text-center space-y-4">
          <p className="text-red-400 text-sm">{error}</p>
          <button
            onClick={() => fetchAnalytics()}
            className="px-4 py-2 bg-red-500 text-white rounded-full text-xs font-semibold hover:bg-red-600 transition-all"
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* Main Layout Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Activation Funnel Analysis (Left 1/3) */}
            <div className="lg:col-span-1 bg-bg2/40 border border-border/60 rounded-[24px] p-6 space-y-6">
              <div className="flex items-center gap-2 border-b border-border/40 pb-4">
                <TrendingUp className="w-5 h-5 text-accent" />
                <h2 className="text-lg font-medium text-text">Activation Funnel</h2>
              </div>

              <div className="space-y-5">
                {funnel.map((step, idx) => {
                  const previousStep = idx > 0 ? funnel[idx - 1] : null;
                  const dropoff = previousStep 
                    ? Math.round((1 - (step.count / previousStep.count)) * 100) 
                    : 0;

                  return (
                    <div key={step.step} className="space-y-1.5 relative">
                      {idx > 0 && (
                        <div className="absolute -top-3.5 left-4 text-[10px] font-semibold text-rose-400/80 bg-bg2 px-1.5 py-0.5 rounded border border-border/30 z-10 scale-90">
                          -{dropoff}% drop-off
                        </div>
                      )}
                      <div className="flex justify-between text-xs">
                        <span className="text-text font-medium">{step.name}</span>
                        <span className="text-text2 font-semibold">
                          {step.count} ({step.percent}%)
                        </span>
                      </div>
                      <div className="h-2 w-full bg-bg3 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-accent to-accent2 rounded-full transition-all duration-500"
                          style={{ width: `${step.percent}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="bg-accent/5 rounded-xl p-3 border border-accent/10 flex gap-2">
                <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                <p className="text-[10px] text-text2 leading-normal">
                  The activation funnel is compiled from user activity (first action logged) across your DB logs. The delta indicates drop-off rates between successive user engagement phases.
                </p>
              </div>
            </div>

            {/* A/B Experiments Management (Right 2/3) */}
            <div className="lg:col-span-2 space-y-6">
              <div className="flex items-center justify-between border-b border-border/40 pb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-teal" />
                  <h2 className="text-lg font-medium text-text">A/B Experiments</h2>
                </div>
                <span className="text-xs text-text3 font-semibold uppercase tracking-wider">
                  {experiments.length} Active Tests
                </span>
              </div>

              <div className="space-y-6">
                {experiments.length === 0 ? (
                  <div className="p-12 border border-dashed border-border rounded-[24px] text-center text-text3 text-sm">
                    No experiments configured. Click "New A/B Test" above to seed a new experiment.
                  </div>
                ) : (
                  experiments.map((expr) => (
                    <div 
                      key={expr.id}
                      className="bg-bg2/40 border border-border/60 rounded-[24px] p-6 space-y-5 transition-all duration-300 hover:border-border2/80 hover:shadow-lg"
                    >
                      {/* Header */}
                      <div className="flex justify-between items-start gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-text text-base">{expr.name}</h3>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              expr.status === 'running' 
                                ? 'bg-teal/15 text-teal' 
                                : expr.status === 'completed'
                                ? 'bg-accent/15 text-accent2'
                                : 'bg-gray-500/15 text-text3'
                            }`}>
                              {expr.status}
                            </span>
                          </div>
                          <p className="text-xs text-text2 mt-1 leading-relaxed">{expr.description}</p>
                        </div>

                        <button
                          onClick={() => handleStatusToggle(expr.id, expr.status)}
                          className={`p-2 rounded-full border transition-all flex items-center justify-center ${
                            expr.status === 'running' 
                              ? 'bg-amber-500/15 border-amber-500/20 text-amber-400 hover:bg-amber-500/30' 
                              : 'bg-teal/15 border-teal/20 text-teal hover:bg-teal/30'
                          }`}
                          title={expr.status === 'running' ? 'Pause Experiment' : 'Start Experiment'}
                        >
                          {expr.status === 'running' ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                        </button>
                      </div>

                      {/* Stat Breakdown Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-bg3/40 rounded-2xl p-4 border border-border/30">
                        {expr.variants.map((v, idx) => (
                          <div key={v.variant} className="space-y-1">
                            <div className="flex justify-between text-xs text-text2">
                              <span className="font-medium flex items-center gap-1.5">
                                <span className={`w-2 h-2 rounded-full ${idx === 0 ? 'bg-accent' : 'bg-teal'}`} />
                                Variant: {v.variant}
                              </span>
                              <span className="font-semibold text-text">{v.conversion_rate}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-bg rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${idx === 0 ? 'bg-accent' : 'bg-teal'}`}
                                style={{ width: `${v.conversion_rate}%` }}
                              />
                            </div>
                            <div className="flex justify-between text-[10px] text-text3 pt-0.5">
                              <span>Sample size: {v.sample_size}</span>
                              <span>Conversions: {v.conversions}</span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Analysis Verdict */}
                      <div className="flex items-start gap-3 bg-bg3/30 border border-border/30 rounded-2xl p-4">
                        <CheckCircle2 className={`w-5 h-5 shrink-0 mt-0.5 ${
                          expr.is_significant ? 'text-teal' : 'text-text3'
                        }`} />
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-text">Verdict & Statistical Significance</span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                              expr.is_significant ? 'bg-teal/15 text-teal' : 'bg-yellow-500/15 text-yellow-400'
                            }`}>
                              {expr.is_significant ? 'Significant' : 'Inconclusive'}
                            </span>
                          </div>
                          <p className="text-xs text-text2 leading-normal">
                            {expr.conclusion}
                          </p>
                          <div className="text-[10px] text-text3 flex gap-4 pt-1">
                            <span>Confidence metrics: p-value = <b>{expr.p_value}</b></span>
                            <span>Improvement: <b>{expr.improvement_delta > 0 ? `+${expr.improvement_delta}%` : `${expr.improvement_delta}%`}</b></span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Create Experiment Modal Dialog */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-bg2 border border-border rounded-[28px] max-w-md w-full p-6 space-y-6 shadow-2xl animate-scaleUp">
            <div>
              <h3 className="text-lg font-medium text-text">Launch New A/B Experiment</h3>
              <p className="text-xs text-text2 mt-1">Configure user routing variants to run hypothesis-driven design optimizations.</p>
            </div>

            <form onSubmit={handleCreateExperiment} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-text2">Experiment Code Name (Unique)</label>
                <input
                  type="text"
                  required
                  value={newExpName}
                  onChange={(e) => setNewExpName(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                  placeholder="e.g. morning_routine_style"
                  className="w-full bg-bg3 border border-border rounded-xl px-4 py-2.5 text-xs text-text placeholder:text-text3 focus:outline-none focus:border-accent/40"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-text2">Hypothesis / Description</label>
                <textarea
                  required
                  value={newExpDesc}
                  onChange={(e) => setNewExpDesc(e.target.value)}
                  placeholder="e.g. Testing visual cards layout with recommended badges to improve breathwork completions."
                  className="w-full bg-bg3 border border-border rounded-xl px-4 py-2.5 text-xs text-text placeholder:text-text3 focus:outline-none focus:border-accent/40 resize-none h-20"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-text2">Variants (Comma-separated)</label>
                <input
                  type="text"
                  required
                  value={newExpVariants}
                  onChange={(e) => setNewExpVariants(e.target.value)}
                  placeholder="control, creative"
                  className="w-full bg-bg3 border border-border rounded-xl px-4 py-2.5 text-xs text-text placeholder:text-text3 focus:outline-none focus:border-accent/40"
                />
              </div>

              <div className="pt-2 flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-text3 hover:text-text transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-5 py-2 bg-accent hover:bg-accent2 text-white rounded-full font-semibold text-xs transition-all disabled:opacity-40"
                >
                  {creating ? 'Registering...' : 'Launch Experiment â¦'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
