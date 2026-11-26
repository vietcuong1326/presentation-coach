import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api, ProjectData, EvaluationListItem } from '../api/client'
import { AppHeader } from '../components/AppHeader'
import { EvaluationStatusBadge, PresentationTypeBadge } from '../components/StatusBadge'
import {
  PlusCircle,
  AlertCircle,
  FileText,
  Trash2,
  Loader2,
  Calendar,
  History,
  ArrowRight,
  Clock,
  MessageSquare,
} from 'lucide-react'

export default function Dashboard() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [projects, setProjects] = useState<ProjectData[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [projectsError, setProjectsError] = useState('')
  const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([])
  const [loadingEvals, setLoadingEvals] = useState(true)
  const [evalsError, setEvalsError] = useState('')
  const [activeTab, setActiveTab] = useState<'projects' | 'history'>('projects')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deletingEvalId, setDeletingEvalId] = useState<string | null>(null)

  const loadProjects = async () => {
    if (!token) return
    setLoadingProjects(true)
    setProjectsError('')
    try {
      const data = await api.listProjects(token)
      setProjects(data)
    } catch (err: any) {
      setProjectsError(err.message || 'Failed to load projects.')
    } finally {
      setLoadingProjects(false)
    }
  }

  const loadEvaluations = async () => {
    if (!token) return
    setLoadingEvals(true)
    setEvalsError('')
    try {
      const data = await api.listEvaluations(token)
      setEvaluations(data.filter((ev) => ev.status === 'COMPLETED' || ev.status === 'PARTIAL'))
    } catch (err: any) {
      setEvalsError(err.message || 'Failed to load evaluation history.')
    } finally {
      setLoadingEvals(false)
    }
  }

  useEffect(() => {
    if (token) {
      loadProjects()
      loadEvaluations()
    }
  }, [token])

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!token) return
    if (!confirm('Delete this project and its evaluations?')) return

    setDeletingId(id)
    try {
      await api.deleteProject(token, id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
      setEvaluations((prev) => prev.filter((ev) => ev.project_id !== id))
    } catch (err: any) {
      alert(`Failed to delete project: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  const handleDeleteEvaluation = async (id: string) => {
    if (!token) return
    if (!confirm('Delete this evaluation, report, and chat history?')) return

    setDeletingEvalId(id)
    try {
      await api.deleteEvaluation(token, id)
      setEvaluations((prev) => prev.filter((ev) => ev.id !== id))
    } catch (err: any) {
      alert(`Failed to delete evaluation: ${err.message}`)
    } finally {
      setDeletingEvalId(null)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <AppHeader showUserMenu />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Presentations</h1>
            <p className="text-sm text-slate-600 mt-1">
              Upload slides and audio for evidence-based coaching feedback.
            </p>
          </div>

          <Link
            to="/projects/new"
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-sm hover:bg-blue-700 transition shrink-0"
          >
            <PlusCircle className="w-4 h-4" />
            New Evaluation
          </Link>
        </div>

        <div className="flex items-center gap-1 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('projects')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition ${
              activeTab === 'projects'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText className="w-4 h-4" />
            Projects ({projects.length})
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition ${
              activeTab === 'history'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <History className="w-4 h-4" />
            History ({evaluations.length})
          </button>
        </div>

        {activeTab === 'projects' && (
          <div>
            {loadingProjects ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <p className="text-sm text-slate-500">Loading projects...</p>
              </div>
            ) : projectsError ? (
              <div className="bg-rose-50 rounded-2xl border border-rose-200 p-6 text-center space-y-2">
                <AlertCircle className="w-6 h-6 text-rose-500 mx-auto" />
                <p className="text-sm font-medium text-rose-800">{projectsError}</p>
                <button
                  onClick={loadProjects}
                  className="text-xs font-semibold text-rose-700 underline hover:text-rose-900"
                >
                  Try again
                </button>
              </div>
            ) : projects.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center flex flex-col items-center justify-center space-y-3">
                <FileText className="w-10 h-10 text-slate-300 stroke-1" />
                <h2 className="text-base font-semibold text-slate-800">No projects yet</h2>
                <p className="text-xs text-slate-500 max-w-sm">
                  Create a presentation project to upload your slides and recording.
                </p>
                <Link
                  to="/projects/new"
                  className="mt-1 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
                >
                  <PlusCircle className="w-4 h-4" />
                  New Evaluation
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {projects.map((proj) => (
                  <div
                    key={proj.id}
                    onClick={() => navigate(`/projects/${proj.id}`)}
                    className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition cursor-pointer flex flex-col justify-between space-y-4"
                  >
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <PresentationTypeBadge
                          type={proj.presentation_type}
                          memberCount={proj.presentation_type === 'GROUP' ? proj.members.length : undefined}
                        />
                        <button
                          onClick={(e) => handleDeleteProject(proj.id, e)}
                          disabled={deletingId === proj.id}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                          title="Delete project"
                        >
                          {deletingId === proj.id ? (
                            <Loader2 className="w-4 h-4 animate-spin text-rose-600" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      <h2 className="font-semibold text-slate-900 text-base line-clamp-1">
                        {proj.title}
                      </h2>
                      {proj.topic && (
                        <p className="text-xs text-slate-500 line-clamp-1">{proj.topic}</p>
                      )}
                    </div>

                    <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(proj.created_at).toLocaleDateString()}
                      </span>
                      <span className="font-medium text-blue-600 inline-flex items-center gap-1">
                        Open <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            {loadingEvals ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <p className="text-sm text-slate-500">Loading history...</p>
              </div>
            ) : evalsError ? (
              <div className="bg-rose-50 rounded-2xl border border-rose-200 p-6 text-center space-y-2">
                <AlertCircle className="w-6 h-6 text-rose-500 mx-auto" />
                <p className="text-sm font-medium text-rose-800">{evalsError}</p>
                <button
                  onClick={loadEvaluations}
                  className="text-xs font-semibold text-rose-700 underline hover:text-rose-900"
                >
                  Try again
                </button>
              </div>
            ) : evaluations.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center flex flex-col items-center justify-center space-y-3">
                <History className="w-10 h-10 text-slate-300 stroke-1" />
                <h2 className="text-base font-semibold text-slate-800">No completed evaluations yet</h2>
                <p className="text-xs text-slate-500 max-w-sm">
                  Completed reports from your projects will appear here.
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden shadow-sm">
                {evaluations.map((ev) => (
                  <div
                    key={ev.id}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/70 transition"
                  >
                    <div className="space-y-1.5 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <EvaluationStatusBadge status={ev.status} />
                        <span className="text-xs text-slate-400">Rubric {ev.rubric_version}</span>
                      </div>

                      <h3 className="text-base font-semibold text-slate-900 truncate">
                        {ev.project_title || 'Presentation Project'}
                      </h3>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          {new Date(ev.created_at).toLocaleString()}
                        </span>
                        {ev.completed_at && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            {new Date(ev.completed_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => navigate(`/evaluations/${ev.id}/report`)}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition border border-blue-200"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        Reopen Report
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => navigate(`/evaluations/${ev.id}/report?chat=open`)}
                        className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition border border-slate-200"
                        title="Open AI Coach chat"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        Chat
                      </button>
                      <button
                        onClick={() => handleDeleteEvaluation(ev.id)}
                        disabled={deletingEvalId === ev.id}
                        className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                        title="Delete evaluation"
                      >
                        {deletingEvalId === ev.id ? (
                          <Loader2 className="w-4 h-4 animate-spin text-rose-600" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
