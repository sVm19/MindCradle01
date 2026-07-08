import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { ai as aiApi } from '@/lib/api';
import { 
  KnowledgeNode, 
  KnowledgeChapter, 
  GrowthMetricItem,
  KnowledgeComparisonResponse 
} from '@/lib/api';
import { 
  ArrowLeft, 
  Check, 
  Trash2, 
  HelpCircle, 
  TrendingUp, 
  Calendar, 
  Target, 
  Flame, 
  Smile, 
  AlertTriangle,
  FileText,
  CheckCircle2,
  Compass
} from 'lucide-react';
import GuestGate from '@/app/components/GuestGate';
import { useAuth } from '@/lib/auth';

const METRIC_LABELS: Record<string, { label: string; desc: string }> = {
  mood_average: { label: "Mood Average", desc: "Your average logged emotional state" },
  consistency_index: { label: "Consistency Index", desc: "Rate of morning and evening ritual completions" },
  journal_depth: { label: "Reflection Depth", desc: "Detailed introspection and entry lengths" },
  emotional_regulation: { label: "Emotional Regulation", desc: "Percentage of low mood moments addressed by writing" },
  self_awareness: { label: "Self-Awareness", desc: "Breadth of themes and emotional patterns extracted" },
  stress_resilience: { label: "Stress Resilience", desc: "Pace of mood recovery after challenging days" },
  goal_clarity: { label: "Goal Clarity", desc: "Explicitly defined and active progress intentions" },
  linguistic_growth: { label: "Linguistic Expressiveness", desc: "Complexity and vocabulary variance of reflections" },
  pattern_awareness: { label: "Meta-Pattern Awareness", desc: "Confirmed patterns and self-reflections" },
  positive_momentum: { label: "Positive Momentum", desc: "Upward trend in emotional snapshots" }
};

export default function Understanding() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [nodes, setNodes] = useState<KnowledgeNode[]>([]);
  const [chapters, setChapters] = useState<KnowledgeChapter[]>([]);
  const [metrics, setMetrics] = useState<GrowthMetricItem[]>([]);
  const [comparison, setComparison] = useState<KnowledgeComparisonResponse | null>(null);
  
  const [activeTab, setActiveTab] = useState<'nodes' | 'chapters' | 'metrics'>('nodes');
  const [filterType, setFilterType] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);

  // For editing node labels
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [editLabelText, setEditLabelText] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [graphRes, chapRes, metricRes, compRes] = await Promise.all([
        aiApi.getKnowledgeGraph(),
        aiApi.getLifeChapters(),
        aiApi.getGrowthMetrics(),
        aiApi.getChapterComparison()
      ]);
      setNodes(graphRes.nodes || []);
      setChapters(chapRes.chapters || []);
      setMetrics(metricRes.metrics || []);
      setComparison(compRes);
    } catch (err) {
      console.error('Failed to load understanding graph:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user]);

  const handleToggleConfirm = async (node: KnowledgeNode) => {
    try {
      const updated = await aiApi.updateKnowledgeNode(node.id, { 
        is_confirmed: !node.is_confirmed 
      });
      setNodes(prev => prev.map(n => n.id === node.id ? updated : n));
    } catch (err) {
      console.error('Failed to confirm node:', err);
    }
  };

  const handleDeleteNode = async (nodeId: string) => {
    if (!window.confirm("Are you sure you want ARIA to forget this theme? This will clear it from ARIA's active memories.")) return;
    try {
      await aiApi.deleteKnowledgeNode(nodeId);
      setNodes(prev => prev.filter(n => n.id !== nodeId));
    } catch (err) {
      console.error('Failed to delete node:', err);
    }
  };

  const handleStartEditLabel = (node: KnowledgeNode) => {
    setEditingNodeId(node.id);
    setEditLabelText(node.label);
  };

  const handleSaveLabel = async (nodeId: string) => {
    if (!editLabelText.trim()) return;
    try {
      const updated = await aiApi.updateKnowledgeNode(nodeId, { 
        label: editLabelText.trim() 
      });
      setNodes(prev => prev.map(n => n.id === nodeId ? updated : n));
      setEditingNodeId(null);
    } catch (err) {
      console.error('Failed to update node label:', err);
    }
  };

  if (!user) {
    return (
      <GuestGate
        title="ARIA's Understanding"
        description="Review, modify, or manage how your AI companion builds a Personal Knowledge Graph of your growth."
        icon={<Compass className="w-8 h-8 text-accent" />}
      />
    );
  }

  const nodeTypes = Array.from(new Set(nodes.map(n => n.node_type)));
  const filteredNodes = nodes.filter(n => filterType === 'all' || n.node_type === filterType);

  return (
    <div className="space-y-8 animate-fadeIn text-left max-w-4xl mx-auto">
      {/* Back & Title */}
      <div className="flex items-center gap-4">
        <button 
          onClick={() => navigate('/settings')}
          className="p-2 hover:bg-bg2 border border-border/50 rounded-lg text-text3 hover:text-text transition-all cursor-pointer"
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <div className="text-xs text-accent tracking-[0.1em] uppercase mb-1">COMPREHENSION</div>
          <h1 className="text-3xl font-light text-text">ARIA's Understanding</h1>
        </div>
      </div>

      {/* Intro Description */}
      <div className="bg-bg2 border border-border/80 rounded-2xl p-5 text-sm text-text2 leading-relaxed">
        This panel displays the underlying **Personal Knowledge Graph** ARIA builds as you interact with MindCradle. 
        ARIA uses this structured understanding to personalize conversation context, match habits, and identify life chapters. 
        In the interest of full privacy, you are free to correct labels, confirm patterns, or delete nodes ARIA has logged.
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border/60">
        <button
          onClick={() => setActiveTab('nodes')}
          className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 cursor-pointer ${
            activeTab === 'nodes' ? 'border-accent text-accent' : 'border-transparent text-text3 hover:text-text'
          }`}
        >
          Themes & Concepts ({nodes.length})
        </button>
        <button
          onClick={() => setActiveTab('chapters')}
          className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 cursor-pointer ${
            activeTab === 'chapters' ? 'border-accent text-accent' : 'border-transparent text-text3 hover:text-text'
          }`}
        >
          Life Chapters ({chapters.length})
        </button>
        <button
          onClick={() => setActiveTab('metrics')}
          className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 cursor-pointer ${
            activeTab === 'metrics' ? 'border-accent text-accent' : 'border-transparent text-text3 hover:text-text'
          }`}
        >
          Growth Dimensions ({metrics.length})
        </button>
      </div>

      {isLoading ? (
        <div className="py-12 flex justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        </div>
      ) : (
        <>
          {/* TAB 1: NODES BROWSER */}
          {activeTab === 'nodes' && (
            <div className="space-y-6">
              {/* Type Filter Pill Selectors */}
              <div className="flex flex-wrap gap-1.5">
                <button
                  onClick={() => setFilterType('all')}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                    filterType === 'all' 
                      ? 'bg-accent/15 border-accent/30 text-accent2' 
                      : 'bg-bg2 border-border/60 text-text3 hover:text-text'
                  }`}
                >
                  All Themes
                </button>
                {nodeTypes.map(t => (
                  <button
                    key={t}
                    onClick={() => setFilterType(t)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer capitalize ${
                      filterType === t 
                        ? 'bg-accent/15 border-accent/30 text-accent2' 
                        : 'bg-bg2 border-border/60 text-text3 hover:text-text'
                    }`}
                  >
                    {t}s
                  </button>
                ))}
              </div>

              {filteredNodes.length === 0 ? (
                <div className="py-12 text-center text-xs text-text3 border border-dashed border-border rounded-2xl">
                  No themes logged yet in this category. Write in your journal to help ARIA learn.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredNodes.map(node => (
                    <div 
                      key={node.id} 
                      className={`border rounded-2xl p-4 bg-bg2 flex flex-col justify-between transition-all hover:shadow-md ${
                        node.is_confirmed ? 'border-accent/40 bg-accent/[0.02]' : 'border-border'
                      }`}
                    >
                      <div className="space-y-2">
                        {/* Type pill & valence indicator */}
                        <div className="flex justify-between items-center">
                          <span className="text-[10px] text-accent uppercase tracking-wider font-semibold">
                            {node.node_type}
                          </span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-md font-medium ${
                            node.valence > 0.2 ? 'bg-emerald-500/10 text-emerald-600' :
                            node.valence < -0.2 ? 'bg-rose-500/10 text-rose-600' : 'bg-bg3 text-text3'
                          }`}>
                            {node.valence > 0.2 ? 'Positive' : node.valence < -0.2 ? 'Challenging' : 'Neutral'}
                          </span>
                        </div>

                        {/* Editable label */}
                        {editingNodeId === node.id ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={editLabelText}
                              onChange={(e) => setEditLabelText(e.target.value)}
                              className="flex-1 bg-bg px-3 py-1 border border-accent rounded-lg text-sm text-text focus:outline-none"
                              autoFocus
                            />
                            <button
                              onClick={() => handleSaveLabel(node.id)}
                              className="px-2.5 py-1 bg-accent text-bg rounded-lg text-xs font-semibold cursor-pointer"
                            >
                              Save
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <h3 
                              onClick={() => handleStartEditLabel(node)}
                              className="text-base font-medium text-text cursor-pointer hover:underline decoration-dashed decoration-accent/60"
                              title="Click to edit name"
                            >
                              {node.label}
                            </h3>
                          </div>
                        )}

                        <p className="text-xs text-text3">
                          Reason: {node.source_reason || 'Identified via patterns'}
                        </p>
                      </div>

                      {/* Info metrics & action footer */}
                      <div className="flex justify-between items-center border-t border-border/40 pt-3 mt-4">
                        <div className="flex gap-3 text-[10px] text-text3">
                          <span>Mentions: <strong>{node.mention_count}</strong></span>
                          <span>Confidence: <strong>{Math.round(node.confidence * 100)}%</strong></span>
                        </div>

                        <div className="flex gap-2">
                          {/* Confirm pattern button */}
                          <button
                            onClick={() => handleToggleConfirm(node)}
                            className={`p-1.5 border rounded-lg cursor-pointer transition-all ${
                              node.is_confirmed 
                                ? 'bg-accent border-accent text-bg hover:opacity-95' 
                                : 'bg-bg3 border-border/60 text-text3 hover:text-text hover:bg-bg4'
                            }`}
                            title={node.is_confirmed ? "Unconfirm this theme" : "Confirm this theme matches you"}
                          >
                            <Check size={12} />
                          </button>

                          {/* Delete button */}
                          <button
                            onClick={() => handleDeleteNode(node.id)}
                            className="p-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose rounded-lg cursor-pointer transition-all"
                            title="Forget theme"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: LIFE CHAPTERS */}
          {activeTab === 'chapters' && (
            <div className="space-y-6">
              {/* Cross-Chapter Comparison Panel */}
              {comparison && comparison.previous_chapter_title !== 'N/A' && (
                <div className="bg-bg3/65 border border-border rounded-2xl p-5 space-y-4 mb-8">
                  <div className="flex items-center gap-2 text-xs font-semibold text-accent uppercase tracking-wider">
                    <TrendingUp size={14} />
                    <span>Cross-Chapter Growth: {comparison.previous_chapter_title} ➔ {comparison.current_chapter_title}</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Improvements */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-text uppercase tracking-wider">Key Growth Shifts</h4>
                      <ul className="space-y-1.5">
                        {comparison.improvements.map((imp, idx) => (
                          <li key={idx} className="text-xs text-text2 flex items-start gap-2">
                            <span className="text-emerald-500 shrink-0 font-bold">✓</span>
                            <span>{imp}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Challenge */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-text uppercase tracking-wider">Remaining Core Challenge</h4>
                      <p className="text-xs text-text2 leading-relaxed bg-bg2/40 border border-border/30 rounded-xl p-3">
                        {comparison.challenge}
                      </p>
                    </div>
                  </div>

                  {/* Compared Metrics Row */}
                  {comparison.comparison_metrics && comparison.comparison_metrics.length > 0 && (
                    <div className="border-t border-border/40 pt-3 flex gap-6 flex-wrap">
                      {comparison.comparison_metrics.map(metric => (
                        <div key={metric.metric_type} className="text-xs text-text3 flex items-center gap-1.5">
                          <span>{metric.metric_type}:</span>
                          <span className="font-semibold text-text">{metric.current_value}</span>
                          <span className={`text-[10px] font-bold ${metric.delta >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                            ({metric.delta >= 0 ? '+' : ''}{metric.delta})
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {chapters.length === 0 ? (
                <div className="py-12 text-center text-xs text-text3 border border-dashed border-border rounded-2xl">
                  No life chapters identified yet. Write regularly so ARIA can map your journey chapters.
                </div>
              ) : (
                <div className="relative border-l border-border/60 pl-6 ml-4 space-y-8 text-left">
                  {chapters.map((ch, idx) => (
                    <div key={ch.id} className="relative">
                      {/* Timeline dot */}
                      <span className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                        ch.is_current 
                          ? 'bg-accent border-accent text-bg ring-4 ring-accent/15' 
                          : 'bg-bg border-border text-text3'
                      }`}>
                        {ch.is_current && <span className="w-1.5 h-1.5 bg-bg rounded-full" />}
                      </span>

                      {/* Card block */}
                      <div className="bg-bg2 border border-border/80 rounded-2xl p-5 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1">
                          <div>
                            <span className="text-[10px] text-accent font-semibold tracking-wider uppercase">
                              CHAPTER {ch.chapter_number} {ch.is_current && '· CURRENT'}
                            </span>
                            <h3 className="text-lg font-medium text-text mt-0.5">{ch.title}</h3>
                          </div>
                          <span className="text-xs text-text3 bg-bg3/60 px-2.5 py-1 rounded-md">
                            {ch.start_date} — {ch.end_date || 'Present'}
                          </span>
                        </div>

                        {ch.theme_summary && (
                          <p className="text-sm text-text2 leading-relaxed">
                            {ch.theme_summary}
                          </p>
                        )}

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                          <div className="bg-bg3/30 border border-border/30 rounded-xl p-2.5">
                            <span className="text-[10px] text-text3 uppercase block">Dominant Emotion</span>
                            <span className="font-semibold text-text mt-0.5 block capitalize">{ch.dominant_emotion || 'calm'}</span>
                          </div>
                          <div className="bg-bg3/30 border border-border/30 rounded-xl p-2.5">
                            <span className="text-[10px] text-text3 uppercase block">Avg Mood Score</span>
                            <span className="font-semibold text-text mt-0.5 block">{ch.mood_average ? `${ch.mood_average}/10` : '—'}</span>
                          </div>
                          <div className="bg-bg3/30 border border-border/30 rounded-xl p-2.5">
                            <span className="text-[10px] text-text3 uppercase block">Themes Tracked</span>
                            <span className="font-semibold text-text mt-0.5 block">{ch.dominant_themes?.length || 0} themes</span>
                          </div>
                          <div className="bg-bg3/30 border border-border/30 rounded-xl p-2.5">
                            <span className="text-[10px] text-text3 uppercase block">Goals Initiated</span>
                            <span className="font-semibold text-text mt-0.5 block">{ch.goals_started?.length || 0} goals</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: GROWTH DIMENSIONS */}
          {activeTab === 'metrics' && (
            <div className="space-y-6">
              {metrics.length === 0 ? (
                <div className="py-12 text-center text-xs text-text3 border border-dashed border-border rounded-2xl">
                  Growth metrics are computed nightly. Check back tomorrow morning.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {metrics.map(m => {
                    const meta = METRIC_LABELS[m.metric_type] || { label: m.metric_type, desc: "Computed growth score" };
                    return (
                      <div key={`${m.metric_type}-${m.period}`} className="bg-bg2 border border-border/80 rounded-2xl p-5 space-y-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="text-base font-medium text-text">{meta.label}</h3>
                            <p className="text-xs text-text3 mt-0.5">{meta.desc}</p>
                          </div>
                          <span className="text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-md font-semibold">
                            {m.period} window
                          </span>
                        </div>

                        {/* Score bar */}
                        <div className="space-y-1 pt-1">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-text2">Value: {Math.round(m.value)}/100</span>
                            {m.delta !== null && m.delta !== undefined && m.delta !== 0 && (
                              <span className={`flex items-center gap-0.5 font-semibold ${
                                m.delta > 0 ? 'text-emerald-500' : 'text-rose-500'
                              }`}>
                                <TrendingUp size={12} className={m.delta < 0 ? 'rotate-180' : ''} />
                                <span>{m.delta > 0 ? '+' : ''}{Math.round(m.delta)}</span>
                              </span>
                            )}
                          </div>
                          <div className="w-full h-2.5 bg-bg border border-border rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-accent transition-all duration-500" 
                              style={{ width: `${Math.max(10, Math.min(100, m.value))}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
