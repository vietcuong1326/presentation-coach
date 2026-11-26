import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api, ProjectData, UploadedFileResponse, EvaluationListItem } from '../api/client'
import { AppHeader } from '../components/AppHeader'
import { EvaluationStatusBadge, PresentationTypeBadge } from '../components/StatusBadge'
import {
  Sparkles,
  ArrowLeft,
  Upload,
  FileText,
  Volume2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  ChevronRight,
  Eye,
  History,
  ArrowRight,
  MessageSquare,
  Trash2,
} from 'lucide-react'

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const { token } = useAuth()
  const navigate = useNavigate()

  const [project, setProject] = useState<ProjectData | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState('')

  const [slideFile, setSlideFile] = useState<UploadedFileResponse | null>(null)
  const [uploadingSlide, setUploadingSlide] = useState(false)
  const [slideError, setSlideError] = useState('')
  const [showSlidePreview, setShowSlidePreview] = useState(false)

  const [mediaFile, setMediaFile] = useState<UploadedFileResponse | null>(null)
  const [uploadingMedia, setUploadingMedia] = useState(false)
  const [mediaError, setMediaError] = useState('')

  const [startingEval, setStartingEval] = useState(false)
  const [evalError, setEvalError] = useState('')
  const [projectEvals, setProjectEvals] = useState<EvaluationListItem[]>([])
  const [deletingEvalId, setDeletingEvalId] = useState<string | null>(null)

  const loadProjectEvals = async () => {
    if (!token || !projectId) return
    try {
      const data = await api.listProjectEvaluations(token, projectId)
      setProjectEvals(data.filter((ev) => ev.status === 'COMPLETED' || ev.status === 'PARTIAL'))
    } catch (err) {
      console.error('Failed to load project evaluations:', err)
    }
  }

  const handleDeleteEvaluation = async (evalId: string) => {
    if (!token) return
    if (!confirm('Delete this evaluation and its chat history?')) return
    setDeletingEvalId(evalId)
    try {
      await api.deleteEvaluation(token, evalId)
      setProjectEvals((prev) => prev.filter((ev) => ev.id !== evalId))
    } catch (err: any) {
      alert(`Failed to delete evaluation: ${err.message}`)
    } finally {
      setDeletingEvalId(null)
    }
  }

  const handleStartEvaluation = async () => {
    if (!token || !projectId) return
    setEvalError('')
    setStartingEval(true)
    try {
      const res = await api.createEvaluation(token, projectId)
      navigate(`/evaluations/${res.id}/report`)
    } catch (err: any) {
      setEvalError(err.message || 'Failed to start evaluation')
      setStartingEval(false)
    }
  }

  useEffect(() => {
    if (!token || !projectId) return
    setLoading(true)
    api
      .getProject(token, projectId)
      .then((data) => setProject(data))
      .catch((err) => setErrorMsg(err.message || 'Failed to load project details'))
      .finally(() => setLoading(false))

    loadProjectEvals()
  }, [token, projectId])

  const handleSlideUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !token || !projectId) return

    setSlideError('')
    setUploadingSlide(true)
    try {
      const res = await api.uploadProjectFile(token, projectId, file, 'SLIDES')
      setSlideFile(res)
    } catch (err: any) {
      setSlideError(err.message || 'Failed to upload slide file')
    } finally {
      setUploadingSlide(false)
    }
  }

  const handleMediaUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !token || !projectId) return

    setMediaError('')
    setUploadingMedia(true)
    try {
      const ext = file.name.split('.').pop()?.toLowerCase()
      const role = ext === 'mp4' ? 'VIDEO' : 'AUDIO'
      const res = await api.uploadProjectFile(token, projectId, file, role)
      setMediaFile(res)
    } catch (err: any) {
      setMediaError(err.message || 'Failed to upload audio/video file')
    } finally {
      setUploadingMedia(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
          <p className="text-sm text-slate-500 font-medium">Loading project...</p>
        </div>
      </div>
    )
  }

  if (errorMsg || !project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 max-w-md w-full text-center space-y-4">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-slate-900">Project Not Found</h2>
          <p className="text-sm text-slate-500">{errorMsg || 'You do not have access to this project.'}</p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      <AppHeader
        title={project.title}
        backTo="/dashboard"
        maxWidth="5xl"
        rightSlot={
          <PresentationTypeBadge
            type={project.presentation_type}
            memberCount={project.presentation_type === 'GROUP' ? project.members.length : undefined}
          />
        }
      />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 mt-8 space-y-6">
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">{project.title}</h1>
            {project.topic && <p className="text-sm text-slate-600">{project.topic}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-3 border-t border-slate-100 text-xs">
            <div>
              <span className="text-slate-400 block">Audience</span>
              <span className="font-medium text-slate-700">{project.target_audience || 'General'}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Duration</span>
              <span className="font-medium text-slate-700">
                {project.expected_duration_seconds
                  ? `${Math.floor(project.expected_duration_seconds / 60)}m ${project.expected_duration_seconds % 60}s`
                  : 'Flexible'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block">Objectives</span>
              <span className="font-medium text-slate-700 truncate block">
                {project.objectives || 'Not specified'}
              </span>
            </div>
          </div>

          {project.warnings && project.warnings.length > 0 && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs space-y-1">
              <p className="font-semibold flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Timeline notes
              </p>
              {project.warnings.map((w, idx) => (
                <p key={idx} className="pl-5">• {w}</p>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Slides Upload */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-900 text-sm">Slides</h2>
                  <p className="text-xs text-slate-400">PDF or PPTX · Max 20MB</p>
                </div>
              </div>

              {slideFile && (
                <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-semibold">
                  <CheckCircle2 className="w-4 h-4" /> Ready
                </span>
              )}
            </div>

            {slideError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-1.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{slideError}</span>
              </div>
            )}

            {slideFile ? (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">
                      {slideFile.original_filename}
                    </p>
                    <p className="text-xs text-slate-400">
                      {(slideFile.size_bytes / 1024).toFixed(1)} KB · {slideFile.extracted_slides?.length || 0} slides
                    </p>
                  </div>

                  {slideFile.extracted_slides && slideFile.extracted_slides.length > 0 && (
                    <button
                      onClick={() => setShowSlidePreview(!showSlidePreview)}
                      className="inline-flex items-center gap-1 text-xs text-blue-600 font-medium hover:underline shrink-0"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      {showSlidePreview ? 'Hide' : 'Preview'}
                    </button>
                  )}
                </div>

                {showSlidePreview && slideFile.extracted_slides && (
                  <div className="max-h-48 overflow-y-auto space-y-2 pt-2 border-t border-slate-200 text-xs">
                    {slideFile.extracted_slides.map((s) => (
                      <div key={s.page_number} className="p-2.5 bg-white rounded-lg border border-slate-100">
                        <span className="font-semibold text-slate-700">Slide {s.page_number}</span>
                        <p className="text-slate-600 mt-0.5 whitespace-pre-wrap">{s.text || '(No text)'}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <label className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition bg-slate-50/50 hover:bg-blue-50/20">
                <input
                  type="file"
                  accept=".pdf,.pptx"
                  disabled={uploadingSlide}
                  onChange={handleSlideUpload}
                  className="hidden"
                />
                {uploadingSlide ? (
                  <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
                ) : (
                  <Upload className="w-7 h-7 text-slate-400" />
                )}
                <p className="text-xs font-semibold text-slate-700">
                  {uploadingSlide ? 'Uploading & parsing...' : 'Click to upload slides'}
                </p>
              </label>
            )}
          </div>

          {/* Audio / Video Upload */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
                  <Volume2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-900 text-sm">Audio / Video</h2>
                  <p className="text-xs text-slate-400">MP3, WAV, M4A, MP4 · Max 50MB</p>
                </div>
              </div>

              {mediaFile && (
                <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-semibold">
                  <CheckCircle2 className="w-4 h-4" /> Ready
                </span>
              )}
            </div>

            {mediaError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-1.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{mediaError}</span>
              </div>
            )}

            {mediaFile ? (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <p className="text-sm font-semibold text-slate-800 truncate">
                  {mediaFile.original_filename}
                </p>
                <p className="text-xs text-slate-400">
                  {(mediaFile.size_bytes / (1024 * 1024)).toFixed(2)} MB · {mediaFile.file_role}
                </p>
              </div>
            ) : (
              <label className="border-2 border-dashed border-slate-300 hover:border-purple-500 rounded-xl p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition bg-slate-50/50 hover:bg-purple-50/20">
                <input
                  type="file"
                  accept=".mp3,.wav,.m4a,.mp4"
                  disabled={uploadingMedia}
                  onChange={handleMediaUpload}
                  className="hidden"
                />
                {uploadingMedia ? (
                  <Loader2 className="w-7 h-7 animate-spin text-purple-600" />
                ) : (
                  <Upload className="w-7 h-7 text-slate-400" />
                )}
                <p className="text-xs font-semibold text-slate-700">
                  {uploadingMedia ? 'Uploading media...' : 'Click to upload audio or video'}
                </p>
              </label>
            )}
          </div>
        </div>

        {project.presentation_type === 'GROUP' && project.members.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="font-semibold text-slate-900 text-sm">Group Presenters</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {project.members.map((m) => (
                <div key={m.id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <p className="font-semibold text-sm text-slate-900">{m.name}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {m.start_time_seconds != null && m.end_time_seconds != null
                      ? `${m.start_time_seconds}s – ${m.end_time_seconds}s`
                      : 'Time unassigned'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {projectEvals.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <History className="w-4 h-4 text-blue-600" />
              Completed Evaluations ({projectEvals.length})
            </h2>

            <div className="divide-y divide-slate-100">
              {projectEvals.map((ev) => (
                <div key={ev.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2.5">
                    <EvaluationStatusBadge status={ev.status} />
                    <span className="text-xs text-slate-500">
                      {new Date(ev.created_at).toLocaleString()}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => navigate(`/evaluations/${ev.id}/report`)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      Reopen Report
                      <ArrowRight className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => navigate(`/evaluations/${ev.id}/report?chat=open`)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                      title="Open Chat"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      Chat
                    </button>
                    <button
                      onClick={() => handleDeleteEvaluation(ev.id)}
                      disabled={deletingEvalId === ev.id}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                      title="Delete evaluation"
                    >
                      {deletingEvalId === ev.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-600" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 sm:p-7 text-white shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-1 text-center sm:text-left">
              <h2 className="text-lg font-bold flex items-center justify-center sm:justify-start gap-2">
                <Sparkles className="w-5 h-5 text-amber-300" />
                Ready for Evaluation
              </h2>
              <p className="text-xs text-blue-100">
                Transcribe speech, inspect slides, and generate evidence-based feedback.
              </p>
            </div>

            <button
              onClick={handleStartEvaluation}
              disabled={startingEval || uploadingSlide || uploadingMedia}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-blue-700 font-semibold text-sm shadow-sm hover:bg-blue-50 transition shrink-0 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {startingEval ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-blue-700" />
                  Starting...
                </>
              ) : (
                <>
                  Start Evaluation
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          {evalError && (
            <div className="p-3 rounded-lg bg-rose-500/20 border border-rose-200/40 text-rose-100 text-xs flex items-start gap-1.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-300" />
              <span>{evalError}</span>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
