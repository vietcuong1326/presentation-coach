import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api, MemberInput, ProjectInput } from '../api/client'
import { AppHeader } from '../components/AppHeader'
import {
  Users,
  User,
  Plus,
  Trash2,
  AlertCircle,
  Clock,
  Loader2,
} from 'lucide-react'

export default function NewProject() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [topic, setTopic] = useState('')
  const [objectives, setObjectives] = useState('')
  const [targetAudience, setTargetAudience] = useState('')
  const [presentationType, setPresentationType] = useState<'INDIVIDUAL' | 'GROUP'>('INDIVIDUAL')
  const [expectedDuration, setExpectedDuration] = useState<number | ''>(600)

  const [members, setMembers] = useState<MemberInput[]>([
    { name: 'Member 1', start_time_seconds: 0, end_time_seconds: 300 },
    { name: 'Member 2', start_time_seconds: 300, end_time_seconds: 600 },
  ])

  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const handleAddMember = () => {
    const lastMember = members[members.length - 1]
    const nextStart = lastMember?.end_time_seconds || 0
    setMembers([
      ...members,
      {
        name: `Member ${members.length + 1}`,
        start_time_seconds: nextStart,
        end_time_seconds: nextStart + 300,
      },
    ])
  }

  const handleRemoveMember = (index: number) => {
    setMembers(members.filter((_, i) => i !== index))
  }

  const handleMemberChange = (index: number, field: keyof MemberInput, value: any) => {
    const updated = [...members]
    updated[index] = { ...updated[index], [field]: value }
    setMembers(updated)
  }

  const overlapWarnings: string[] = []
  if (presentationType === 'GROUP') {
    const timed = members
      .map((m, idx) => ({ ...m, origIdx: idx }))
      .filter((m) => m.start_time_seconds != null && m.end_time_seconds != null)
      .sort((a, b) => (a.start_time_seconds || 0) - (b.start_time_seconds || 0))

    for (let i = 0; i < timed.length - 1; i++) {
      if ((timed[i].end_time_seconds || 0) > (timed[i + 1].start_time_seconds || 0)) {
        overlapWarnings.push(
          `Overlap between "${timed[i].name}" (${timed[i].start_time_seconds}s - ${timed[i].end_time_seconds}s) and "${timed[i + 1].name}" (${timed[i + 1].start_time_seconds}s - ${timed[i + 1].end_time_seconds}s)`
        )
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    setErrorMsg('')

    if (!title.trim()) {
      setErrorMsg('Please enter a project title.')
      return
    }

    if (presentationType === 'GROUP') {
      if (members.length === 0) {
        setErrorMsg('Group presentations must have at least one member.')
        return
      }
      for (const m of members) {
        if (!m.name.trim()) {
          setErrorMsg('All members must have a name.')
          return
        }
        if (
          m.start_time_seconds != null &&
          m.end_time_seconds != null &&
          m.start_time_seconds >= m.end_time_seconds
        ) {
          setErrorMsg(`Member "${m.name}": Start time must be less than end time.`)
          return
        }
      }
    }

    setSubmitting(true)
    try {
      const payload: ProjectInput = {
        title,
        topic: topic || undefined,
        objectives: objectives || undefined,
        target_audience: targetAudience || undefined,
        presentation_type: presentationType,
        expected_duration_seconds: expectedDuration ? Number(expectedDuration) : null,
        members: presentationType === 'GROUP' ? members : [],
      }

      const created = await api.createProject(token, payload)
      navigate(`/projects/${created.id}`)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      <AppHeader title="New Presentation Project" backTo="/dashboard" maxWidth="4xl" />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 mt-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-5">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
              Project Details
            </h2>

            <div>
              <label className="block text-sm font-medium text-slate-700">
                Title <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Impact of AI in Modern Healthcare"
                className="mt-1.5 block w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">Topic</label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Technology & Medicine"
                  className="mt-1.5 block w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Target Audience</label>
                <input
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="e.g. University students"
                  className="mt-1.5 block w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Objectives</label>
              <textarea
                rows={3}
                value={objectives}
                onChange={(e) => setObjectives(e.target.value)}
                placeholder="Key takeaways or goals for the audience"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">
                Expected Duration (seconds)
              </label>
              <div className="mt-1.5 relative max-w-xs">
                <input
                  type="number"
                  min="1"
                  value={expectedDuration}
                  onChange={(e) => setExpectedDuration(e.target.value ? Number(e.target.value) : '')}
                  className="block w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 text-xs">
                  {expectedDuration ? `${Math.floor(Number(expectedDuration) / 60)}m ${Number(expectedDuration) % 60}s` : ''}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-5">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
              Format & Presenters
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setPresentationType('INDIVIDUAL')}
                className={`p-4 rounded-xl border-2 text-left flex items-start gap-3 transition ${
                  presentationType === 'INDIVIDUAL'
                    ? 'border-blue-600 bg-blue-50/50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <User className={`w-5 h-5 mt-0.5 ${presentationType === 'INDIVIDUAL' ? 'text-blue-600' : 'text-slate-400'}`} />
                <div>
                  <p className="font-semibold text-sm text-slate-900">Individual</p>
                  <p className="text-xs text-slate-500 mt-0.5">Single presenter</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setPresentationType('GROUP')}
                className={`p-4 rounded-xl border-2 text-left flex items-start gap-3 transition ${
                  presentationType === 'GROUP'
                    ? 'border-blue-600 bg-blue-50/50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <Users className={`w-5 h-5 mt-0.5 ${presentationType === 'GROUP' ? 'text-blue-600' : 'text-slate-400'}`} />
                <div>
                  <p className="font-semibold text-sm text-slate-900">Group</p>
                  <p className="text-xs text-slate-500 mt-0.5">Multiple presenters with time ranges</p>
                </div>
              </button>
            </div>

            {presentationType === 'GROUP' && (
              <div className="space-y-4 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800">Members</h3>
                  <button
                    type="button"
                    onClick={handleAddMember}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Member
                  </button>
                </div>

                {overlapWarnings.length > 0 && (
                  <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs space-y-1">
                    <p className="font-medium flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" /> Time overlap detected:
                    </p>
                    {overlapWarnings.map((w, idx) => (
                      <p key={idx} className="pl-5">• {w}</p>
                    ))}
                  </div>
                )}

                <div className="space-y-3">
                  {members.map((member, index) => (
                    <div
                      key={index}
                      className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row items-center gap-3"
                    >
                      <div className="flex-1 w-full sm:w-auto">
                        <label className="text-xs font-medium text-slate-500">Name</label>
                        <input
                          type="text"
                          required
                          value={member.name}
                          onChange={(e) => handleMemberChange(index, 'name', e.target.value)}
                          placeholder="e.g. Alice"
                          className="mt-1 w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white"
                        />
                      </div>

                      <div className="w-full sm:w-32">
                        <label className="text-xs font-medium text-slate-500">Start (sec)</label>
                        <input
                          type="number"
                          min="0"
                          value={member.start_time_seconds ?? ''}
                          onChange={(e) =>
                            handleMemberChange(
                              index,
                              'start_time_seconds',
                              e.target.value ? Number(e.target.value) : null
                            )
                          }
                          className="mt-1 w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white"
                        />
                      </div>

                      <div className="w-full sm:w-32">
                        <label className="text-xs font-medium text-slate-500">End (sec)</label>
                        <input
                          type="number"
                          min="0"
                          value={member.end_time_seconds ?? ''}
                          onChange={(e) =>
                            handleMemberChange(
                              index,
                              'end_time_seconds',
                              e.target.value ? Number(e.target.value) : null
                            )
                          }
                          className="mt-1 w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white"
                        />
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveMember(index)}
                        disabled={members.length <= 1}
                        className="mt-4 sm:mt-5 p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg disabled:opacity-30 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              to="/dashboard"
              className="px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center justify-center px-6 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-sm hover:bg-blue-700 transition disabled:opacity-50"
            >
              {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create & Upload Files'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
