import { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Sparkles, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface AppHeaderProps {
  title?: string
  subtitle?: string
  backTo?: string
  rightSlot?: ReactNode
  showUserMenu?: boolean
  maxWidth?: '4xl' | '5xl' | '6xl'
}

export function AppHeader({
  title = 'AI Presentation Coach',
  subtitle,
  backTo,
  rightSlot,
  showUserMenu = false,
  maxWidth = '6xl',
}: AppHeaderProps) {
  const { user, signOut } = useAuth()
  const widthClass =
    maxWidth === '4xl' ? 'max-w-4xl' : maxWidth === '5xl' ? 'max-w-5xl' : 'max-w-6xl'

  return (
    <header className="bg-white/95 backdrop-blur border-b border-slate-200 sticky top-0 z-20">
      <div className={`${widthClass} mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4`}>
        <div className="flex items-center gap-3 min-w-0">
          {backTo ? (
            <Link
              to={backTo}
              aria-label="Back"
              className="p-2 -ml-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition shrink-0"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
          ) : (
            <Link
              to="/dashboard"
              className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0"
            >
              <Sparkles className="w-4 h-4" />
            </Link>
          )}
          <div className="min-w-0">
            <span className="font-semibold text-slate-900 text-sm sm:text-base leading-tight block truncate">
              {title}
            </span>
            {subtitle && (
              <span className="text-xs text-slate-500 block truncate">{subtitle}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {rightSlot}
          {showUserMenu && (
            <>
              {user?.email && (
                <span className="text-xs text-slate-500 hidden sm:inline-block truncate max-w-[180px]">
                  {user.email}
                </span>
              )}
              <button
                onClick={() => signOut()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

