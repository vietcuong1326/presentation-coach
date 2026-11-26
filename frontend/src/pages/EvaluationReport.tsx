import { useEffect, useState } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ChatCoach from '../components/ChatCoach'
import { AppHeader } from '../components/AppHeader'
import {
  api,
  AnalysisReportData,
  AnalysisReportPayload,
  EvaluationStatusResponse,
  ImprovementItem,
  StrengthItem,
  CriterionResult,
  PriorityAction,
} from '../api/client'
import {
  Sparkles,
  CheckCircle2,
  Clock,
  FileText,
  MessageSquare,
  ShieldAlert,
  Loader2,
  RefreshCw,
  Award,
  TrendingUp,
  Target,
  User,
  Users,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

export default function EvaluationReport() {
  const { evaluationId } = useParams<{ evaluationId: string }>()
  const [searchParams] = useSearchParams()
  const { token } = useAuth()

  const [statusData, setStatusData] = useState<EvaluationStatusResponse | null>(null)
  const [reportData, setReportData] = useState<AnalysisReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState('')
  const [activeTab, setActiveTab] = useState<'ALL' | 'GROUP' | 'INDIVIDUAL'>('ALL')
  const [showRubricDetails, setShowRubricDetails] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(searchParams.get('chat') === 'open')
  const [chatPrompt, setChatPrompt] = useState<string | undefined>(undefined)

  const openChatWithPrompt = (prompt?: string) => {
    setChatPrompt(prompt)
    setIsChatOpen(true)
  }

  const fetchStatusAndReport = async () => {
    if (!token || !evaluationId) return
    try {
      const statusRes = await api.getEvaluationStatus(token, evaluationId)
      setStatusData(statusRes)

      if (statusRes.status === 'COMPLETED' || statusRes.status === 'PARTIAL') {
        const repRes = await api.getEvaluationReport(token, evaluationId)
        if (repRes && repRes.report_json) {
          setReportData(repRes)
        }
      } else if (statusRes.status === 'FAILED') {
        setErrorMsg(statusRes.error_message || 'Evaluation failed.')
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch evaluation report')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatusAndReport()
    const interval = setInterval(() => {
      if (statusData?.status === 'PENDING' || statusData?.status === 'PROCESSING') {
        fetchStatusAndReport()
      }
    }, 4000)
    return () => clearInterval(interval)
  }, [token, evaluationId, statusData?.status])

  if (loading && !statusData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
          <p className="text-sm text-slate-500 font-medium">Loading evaluation...</p>
        </div>
      </div>
    )
  }

  if (statusData && (statusData.status === 'PENDING' || statusData.status === 'PROCESSING')) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center p-6">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm max-w-md w-full text-center space-y-6">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Sparkles className="w-7 h-7 animate-pulse" />
          </div>

          <div className="space-y-1.5">
            <h1 className="text-lg font-bold text-slate-900">Analyzing Presentation</h1>
            <p className="text-xs text-slate-500">
              Transcribing speech, reviewing slides, and assembling evidence-based feedback.
            </p>
          </div>

          <div className="space-y-2.5 text-left border border-slate-200 rounded-xl p-4 bg-slate-50 text-xs">
            <div className="flex items-center gap-2.5 text-emerald-600 font-medium">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Files stored</span>
            </div>
            <div className="flex items-center gap-2.5 text-blue-600 font-medium">
              <RefreshCw className="w-4 h-4 shrink-0 animate-spin" />
              <span>Transcription & slide extraction</span>
            </div>
            <div className="flex items-center gap-2.5 text-slate-400">
              <Clock className="w-4 h-4 shrink-0" />
              <span>Rubric evaluation & coaching synthesis</span>
            </div>
          </div>

          <button
            onClick={fetchStatusAndReport}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition"
          >
            Refresh Status
          </button>
        </div>
      </div>
    )
  }

  if (statusData?.status === 'FAILED' || errorMsg) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm max-w-md w-full text-center space-y-4">
          <ShieldAlert className="w-11 h-11 text-rose-500 mx-auto" />
          <h1 className="text-lg font-bold text-slate-900">Evaluation Failed</h1>
          <p className="text-sm text-slate-500">
            {errorMsg || 'We encountered an error processing this presentation. Failed runs are not saved to history.'}
          </p>
          <div className="pt-2 flex gap-3 justify-center">
            <Link
              to="/dashboard"
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 rounded-xl hover:bg-slate-200 transition"
            >
              Back to Dashboard
            </Link>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded-xl hover:bg-blue-700 transition"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const fallbackReport: AnalysisReportPayload = {
    evaluation_summary: {
      headline: 'Presentation Assessment',
      overall_feedback: 'Assessment ready.',
      evidence_coverage: { evaluated_criteria: 0, not_evaluated_criteria: 0 },
    },
    strengths: [],
    improvements: [],
    criterion_results: [],
    priority_actions: [],
  }

  const report: AnalysisReportPayload = reportData?.report_json || fallbackReport

  const filteredImprovements: ImprovementItem[] = report.improvements.filter((item: ImprovementItem) => {
    if (activeTab === 'GROUP') return item.scope === 'GROUP'
    if (activeTab === 'INDIVIDUAL') return item.scope === 'INDIVIDUAL'
    return true
  })

  const evaluatedList: CriterionResult[] = report.criterion_results.filter((c: CriterionResult) => c.status === 'EVALUATED')
  const earnedPoints = evaluatedList.reduce((acc: number, c: CriterionResult) => acc + (c.score || 0), 0)
  const maxAvailablePoints = evaluatedList.length * 5

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20">
      <AppHeader
        title="Evaluation Report"
        subtitle={`Rubric ${statusData?.rubric_version || 'v1.0'} · ${statusData?.status === 'PARTIAL' ? 'Partial' : 'Complete'}`}
        backTo="/dashboard"
        rightSlot={
          <button
            onClick={() => openChatWithPrompt()}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm transition"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Ask AI Coach
          </button>
        }
      />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* 1. Overall Feedback */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="space-y-1">
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                {report.evaluation_summary.headline}
              </h1>
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-lg text-xs font-medium text-slate-700 shrink-0">
              <Target className="w-3.5 h-3.5 text-slate-500" />
              <span>
                {report.evaluation_summary.evidence_coverage.evaluated_criteria} / 20 evaluated
              </span>
            </div>
          </div>

          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
            {report.evaluation_summary.overall_feedback}
          </p>
        </section>

        {/* 2. Priority Actions */}
        {report.priority_actions && report.priority_actions.length > 0 && (
          <section className="bg-amber-50/70 border border-amber-200 rounded-2xl p-6 sm:p-7 space-y-4">
            <div className="flex items-center gap-2 text-amber-900 font-semibold text-base">
              <TrendingUp className="w-4 h-4 text-amber-600" />
              <h2>Priority Actions</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {report.priority_actions.map((act: PriorityAction, idx: number) => (
                <div key={idx} className="bg-white rounded-xl p-4 border border-amber-200/70 space-y-2">
                  <h3 className="font-semibold text-slate-900 text-sm">{act.title}</h3>
                  <ul className="space-y-1">
                    {act.steps.map((st: string, sIdx: number) => (
                      <li key={sIdx} className="text-xs text-slate-600 flex items-start gap-1.5">
                        <span className="text-amber-500 font-bold">•</span>
                        <span>{st}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 3. Strengths */}
        {report.strengths && report.strengths.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-emerald-600" />
              <h2 className="text-lg font-bold text-slate-900">Strengths</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {report.strengths.map((str: StrengthItem, idx: number) => (
                <div
                  key={idx}
                  className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3" /> Strength
                    </span>
                    <span className="text-xs text-slate-400">
                      {str.related_criteria.join(', ')}
                    </span>
                  </div>
                  <h3 className="font-semibold text-slate-900 text-sm">{str.title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{str.description}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 4. Areas for Improvement */}
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-bold text-slate-900">Areas for Improvement</h2>
            </div>

            <div className="flex bg-slate-200/70 p-1 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setActiveTab('ALL')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  activeTab === 'ALL' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All ({report.improvements.length})
              </button>
              <button
                onClick={() => setActiveTab('GROUP')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  activeTab === 'GROUP' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Group
              </button>
              <button
                onClick={() => setActiveTab('INDIVIDUAL')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  activeTab === 'INDIVIDUAL' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Individual
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {filteredImprovements.map((imp: ImprovementItem) => (
              <div
                key={imp.id}
                className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        imp.severity === 'HIGH'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : imp.severity === 'MEDIUM'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}
                    >
                      {imp.severity}
                    </span>

                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                      {imp.scope === 'GROUP' ? <Users className="w-3 h-3" /> : <User className="w-3 h-3" />}
                      {imp.scope}
                    </span>
                  </div>

                  <span className="text-xs font-medium text-slate-400">
                    {imp.related_criteria.join(', ')}
                  </span>
                </div>

                <h3 className="font-semibold text-slate-900 text-base">{imp.title}</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <span className="font-semibold text-slate-500">Observation</span>
                    <p className="text-slate-700 leading-relaxed">{imp.observation}</p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <span className="font-semibold text-slate-500">Impact</span>
                    <p className="text-slate-700 leading-relaxed">{imp.impact}</p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100 space-y-2 text-xs">
                  <p className="text-blue-900 font-semibold">Recommendation</p>
                  <p className="text-slate-800 leading-relaxed">{imp.recommendation}</p>

                  {imp.example && (
                    <div className="pt-2 border-t border-blue-200/60">
                      <span className="font-semibold text-blue-900">Example: </span>
                      <span className="text-slate-700 italic">"{imp.example}"</span>
                    </div>
                  )}

                  <div className="pt-1 flex justify-end">
                    <button
                      onClick={() => openChatWithPrompt(`Why was this flagged: "${imp.title}"? How can I improve it?`)}
                      className="inline-flex items-center gap-1.5 text-xs text-blue-700 font-semibold hover:text-blue-800 transition"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      Ask Coach
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 5. Rubric Details (Secondary, collapsed by default) */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <button
            onClick={() => setShowRubricDetails(!showRubricDetails)}
            className="w-full p-5 sm:p-6 text-left flex items-center justify-between hover:bg-slate-50/70 transition"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-slate-100 text-slate-700">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <h2 className="font-semibold text-slate-900 text-sm sm:text-base">Rubric Breakdown</h2>
                <p className="text-xs text-slate-500">
                  Criteria without sufficient evidence are marked NOT EVALUATED
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <span className="font-semibold text-slate-800 text-xs sm:text-sm">
                {earnedPoints} / {maxAvailablePoints} pts
              </span>
              {showRubricDetails ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </div>
          </button>

          {showRubricDetails && (
            <div className="p-5 sm:p-6 border-t border-slate-200 bg-slate-50/50 divide-y divide-slate-200">
              {report.criterion_results.map((c: CriterionResult, idx: number) => (
                <div key={idx} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div>
                    <span className="font-semibold text-slate-800">{c.criterion_id}</span>
                    <span className="ml-2 px-2 py-0.5 rounded text-[11px] bg-slate-200 text-slate-600">
                      {c.scope}
                    </span>
                    <p className="text-slate-500 mt-0.5">{c.reason}</p>
                  </div>

                  <div className="sm:text-right shrink-0">
                    {c.status === 'EVALUATED' ? (
                      <span className="font-semibold text-slate-900">
                        {c.score} / 5 {c.level ? `· ${c.level}` : ''}
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-200 text-slate-600">
                        NOT EVALUATED
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <ChatCoach
        evaluationId={evaluationId || ''}
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        initialPrompt={chatPrompt}
      />
    </div>
  )
}
