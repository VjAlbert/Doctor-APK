import { useEffect, useState } from 'react'
import { EngineError } from '../lib/client'
import { useLang } from '../lib/lang'
import { listProjects, type ProjectSummary } from '../lib/workspace'
import { ProjectDetail } from './ProjectDetail'

export function ProjectsView({ aiReady, initialId }: { aiReady: boolean; initialId?: string | null }) {
  const { t } = useLang()
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null)
  const [selected, setSelected] = useState<string | null>(initialId ?? null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (selected) return
    listProjects().then(setProjects).catch((e) => setError(e instanceof EngineError ? e.message : String(e)))
  }, [selected])

  if (selected) return <ProjectDetail id={selected} aiReady={aiReady} onBack={() => setSelected(null)} />
  return (
    <div className="mx-auto w-full max-w-4xl">
      <h1 className="text-3xl font-semibold tracking-tight">{t('proj.title')}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">{t('proj.intro')}</p>
      {error && <p className="mt-4 text-sm text-caution" role="alert">{error}</p>}
      {projects?.length === 0 && <p className="glass mt-8 rounded-2xl p-6 text-center text-sm text-muted">{t('proj.empty')}</p>}
      <ul className="mt-6 grid gap-3">
        {projects?.map((p) => (
          <li key={p.id}>
            <button type="button" onClick={() => setSelected(p.id)} data-testid="project-card"
              className="glass flex w-full items-center justify-between gap-4 rounded-2xl px-6 py-4 text-left transition hover:bg-white/[.04]">
              <span className="min-w-0">
                <span className="block truncate text-lg font-semibold">{p.name}</span>
                <span className="block truncate font-mono text-xs text-dim">{p.package}</span>
              </span>
              <span className="flex shrink-0 gap-2 text-xs">
                {p.open_ideas > 0 && <span className="rounded-full bg-white/[.06] px-2.5 py-1">{p.open_ideas} {t('proj.openIdeas')}</span>}
                {p.open_proposals > 0 && <span className="rounded-full bg-[#fbbf24]/15 px-2.5 py-1 text-[#fbbf24]">{p.open_proposals} {t('proj.openReviews')}</span>}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
