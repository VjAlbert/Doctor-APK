import { useCallback, useEffect, useRef, useState } from 'react'
import { EngineError } from '../lib/client'
import { formatSize } from '../lib/format'
import { useLang } from '../lib/lang'
import type { UiKey } from '../lib/ui'
import {
  addIdea, approveProposal, downloadProjectZip, draftIdea, exportIdeas, getProject, getProposal, importIdeas,
  readProjectFile, rejectProposal, STATUS_COLOR, undoLast, type Idea, type ProjectDetail as Detail, type ProposalView,
} from '../lib/workspace'
import { ArrowLeftIcon, DownloadIcon, SparkIcon } from './Icons'
import { DiffView } from './DiffView'

type Tab = 'spec' | 'ideas' | 'reviews'

function Status({ status }: { status: string }) {
  const { t } = useLang()
  const color = STATUS_COLOR[status] ?? '#8a9bb2'
  return <span className="rounded-full px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider" style={{ color, background: `${color}1a`, border: `1px solid ${color}44` }}>{t(`status.${status}` as UiKey)}</span>
}

const message = (e: unknown) => (e instanceof EngineError ? e.message : String(e))

export function ProjectDetail({ id, aiReady, onBack }: { id: string; aiReady: boolean; onBack: () => void }) {
  const { t, lang } = useLang()
  const [detail, setDetail] = useState<Detail | null>(null)
  const [tab, setTab] = useState<Tab>('spec')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [reviewId, setReviewId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDetail(await getProject(id))
    } catch (e) {
      setError(message(e))
    }
  }, [id])
  useEffect(() => { void refresh() }, [refresh])

  if (error && !detail) return <p className="glass mx-auto mt-10 max-w-xl rounded-2xl p-6 text-center text-sm text-caution" role="alert">{error}</p>
  if (!detail) return null

  const tabs: { id: Tab; label: UiKey; badge?: number }[] = [
    { id: 'spec', label: 'proj.specTab' },
    { id: 'ideas', label: 'proj.ideasTab', badge: detail.open_ideas },
    { id: 'reviews', label: 'proj.reviewsTab', badge: detail.open_proposals },
  ]

  return (
    <div className="mx-auto flex h-full min-h-0 w-full max-w-5xl flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button type="button" onClick={onBack} aria-label={t('proj.back')} className="grid size-9 place-items-center rounded-xl border border-line-strong text-muted transition hover:text-ink"><ArrowLeftIcon size={18} /></button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{detail.name}</h1>
            <p className="font-mono text-xs text-dim">{detail.package}</p>
          </div>
        </div>
        <button type="button" onClick={() => void downloadProjectZip(id).catch((e) => setError(message(e)))}
          className="flex items-center gap-2 rounded-xl border border-line-strong px-3.5 py-2 text-sm text-muted transition hover:text-ink"><DownloadIcon size={16} />{t('proj.zip')}</button>
      </div>

      <div role="tablist" className="glass mt-4 flex w-fit rounded-xl p-1">
        {tabs.map((x) => (
          <button key={x.id} type="button" role="tab" aria-selected={tab === x.id} onClick={() => { setTab(x.id); setNotice(null) }}
            className="flex items-center gap-2 rounded-lg px-4 py-1.5 text-sm font-medium transition"
            style={{ color: tab === x.id ? '#e6edf6' : '#8a9bb2', background: tab === x.id ? 'rgb(34 211 238 / .14)' : 'transparent' }}>
            {t(x.label)}
            {!!x.badge && <span className="rounded-full bg-[#fbbf24] px-1.5 font-mono text-[10px] font-semibold text-bg">{x.badge}</span>}
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-sm text-caution" role="alert">{error}</p>}
      {notice && <p className="mt-3 text-sm text-ok" role="status">{notice}</p>}

      <div className="mt-4 min-h-0 flex-1">
        {tab === 'spec' && (
          <SpecTab detail={detail} aiReady={aiReady} lang={lang} onChange={refresh} onError={setError} onNotice={setNotice}
            onOpenReview={(pid) => { setReviewId(pid); setTab('reviews') }} />
        )}
        {tab === 'ideas' && (
          <IdeasTab detail={detail} aiReady={aiReady} lang={lang} onChange={refresh} onError={setError} onNotice={setNotice}
            onOpenReview={(pid) => { setReviewId(pid); setTab('reviews') }} />
        )}
        {tab === 'reviews' && (
          <ReviewsTab detail={detail} reviewId={reviewId} setReviewId={setReviewId} onChange={refresh} onError={setError} onNotice={setNotice} />
        )}
      </div>
    </div>
  )
}

function SpecTab({ detail, aiReady, lang, onChange, onError, onOpenReview }: TabProps & { aiReady: boolean; lang: 'it' | 'en'; onOpenReview: (id: string) => void }) {
  const { t } = useLang()
  const [path, setPath] = useState('SPEC.md')
  const [content, setContent] = useState('')
  const [working, setWorking] = useState(false)
  useEffect(() => { void readProjectFile(detail.id, path).then(setContent).catch(() => setContent('')) }, [detail.id, path, detail.history.length])
  const hasCode = detail.files.some((f) => /\.(kt|java)$/.test(f.path))

  // The starter project is just an idea with a fixed text: it goes through the same review as any other.
  const generate = async () => {
    setWorking(true)
    onError(null)
    try {
      const idea = await addIdea(detail.id, t('proj.starterIdea'), 'APKGuard')
      const result = await draftIdea(detail.id, idea.id, lang)
      await onChange()
      if (result.proposal) onOpenReview(result.proposal.id)
      else onError(`${t('idea.declined')} ${result.summary}`)
    } catch (e) { onError(message(e)) } finally { setWorking(false) }
  }
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {aiReady && !hasCode && (
        <div className="glass flex flex-wrap items-center gap-4 rounded-2xl px-5 py-3">
          <button type="button" disabled={working} onClick={() => void generate()} data-testid="starter"
            className="flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold disabled:opacity-50"
            style={{ color: '#d8b4fe', background: 'rgb(139 92 246 / .14)', border: '1px solid rgb(139 92 246 / .45)' }}>
            <SparkIcon size={16} />{working ? t('idea.drafting') : t('proj.starter')}
          </button>
          <p className="min-w-0 flex-1 text-xs text-dim">{t('proj.starterNote')}</p>
        </div>
      )}
    <div className="grid min-h-0 flex-1 gap-4 md:grid-cols-[220px_1fr]">
      <nav aria-label={t('spec.files')} className="glass scroll min-h-0 overflow-y-auto rounded-2xl p-2">
        {detail.files.map((f) => (
          <button key={f.path} type="button" onClick={() => setPath(f.path)} aria-current={path === f.path}
            className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-white/[.04]"
            style={{ background: path === f.path ? 'rgb(34 211 238 / .12)' : undefined }}>
            <span className="truncate font-mono text-xs">{f.path}</span><span className="text-[10px] text-dim">{formatSize(f.size)}</span>
          </button>
        ))}
      </nav>
      <pre className="glass scroll min-h-0 overflow-auto whitespace-pre-wrap rounded-2xl p-5 font-mono text-[12.5px] leading-relaxed text-ink/90" data-testid="file-content">{content}</pre>
    </div>
    </div>
  )
}

interface TabProps {
  detail: Detail
  onChange: () => Promise<void>
  onError: (m: string | null) => void
  onNotice: (m: string | null) => void
}

function IdeasTab({ detail, aiReady, lang, onChange, onError, onNotice, onOpenReview }: TabProps & { aiReady: boolean; lang: 'it' | 'en'; onOpenReview: (id: string) => void }) {
  const { t } = useLang()
  const [text, setText] = useState('')
  const [author, setAuthor] = useState(() => { try { return localStorage.getItem('apkguard.author') ?? '' } catch { return '' } })
  const [drafting, setDrafting] = useState<string | null>(null)
  const [declined, setDeclined] = useState<Record<string, string>>({})
  const fileInput = useRef<HTMLInputElement>(null)

  const send = async () => {
    try {
      onError(null)
      try { localStorage.setItem('apkguard.author', author) } catch { /* not remembered */ }
      await addIdea(detail.id, text, author)
      setText('')
      await onChange()
    } catch (e) { onError(message(e)) }
  }

  const draft = async (idea: Idea) => {
    setDrafting(idea.id)
    onError(null)
    try {
      const result = await draftIdea(detail.id, idea.id, lang)
      if (result.declined) setDeclined((d) => ({ ...d, [idea.id]: result.summary }))
      await onChange()
    } catch (e) { onError(message(e)) } finally { setDrafting(null) }
  }

  const share = async () => {
    try {
      const data = await exportIdeas(detail.id)
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: 'application/json' }))
      const a = document.createElement('a')
      a.href = url; a.download = `${detail.id}-ideas.json`; document.body.append(a); a.click(); a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { onError(message(e)) }
  }

  const importFile = async (file: File | undefined) => {
    if (!file) return
    try {
      const result = await importIdeas(detail.id, JSON.parse(await file.text()))
      onNotice(`${t('idea.imported')}: ${result.added} (${result.skipped} ${t('idea.skipped')})`)
      await onChange()
    } catch (e) { onError(e instanceof SyntaxError ? 'Invalid file.' : message(e)) }
  }

  return (
    <div className="scroll h-full overflow-y-auto pb-6 pr-2">
      <section className="glass rounded-2xl p-5">
        <h2 className="mb-3 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('idea.add')}</h2>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={2000} placeholder={t('idea.placeholder')} aria-label={t('idea.add')}
          className="w-full resize-y rounded-xl border border-line-strong bg-black/30 px-3.5 py-2.5 text-sm outline-none focus:border-cyan" />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <input value={author} onChange={(e) => setAuthor(e.target.value)} maxLength={60} placeholder={t('idea.author')} aria-label={t('idea.author')}
            className="w-48 rounded-xl border border-line-strong bg-black/30 px-3.5 py-2 text-sm outline-none focus:border-cyan" />
          <button type="button" disabled={!text.trim()} onClick={() => void send()} className="rounded-xl px-4 py-2 text-sm font-semibold text-bg disabled:opacity-40" style={{ background: '#22d3ee' }}>{t('idea.send')}</button>
          <span className="flex-1" />
          <button type="button" onClick={() => void share()} className="rounded-xl border border-line-strong px-3.5 py-2 text-sm text-muted hover:text-ink">{t('idea.share')}</button>
          <button type="button" onClick={() => fileInput.current?.click()} className="rounded-xl border border-line-strong px-3.5 py-2 text-sm text-muted hover:text-ink">{t('idea.import')}</button>
          <input ref={fileInput} type="file" accept="application/json,.json" hidden onChange={(e) => { void importFile(e.target.files?.[0]); e.target.value = '' }} />
        </div>
      </section>

      {!aiReady && <p className="mt-3 flex items-center gap-2 text-sm text-dim"><SparkIcon size={15} />{t('idea.needAi')}</p>}
      <ul className="mt-4 grid gap-2.5">
        {detail.ideas.length === 0 && <li className="py-8 text-center text-sm text-muted">{t('idea.empty')}</li>}
        {[...detail.ideas].reverse().map((idea) => (
          <li key={idea.id} className="glass rounded-2xl px-5 py-4" data-testid="idea">
            <div className="flex flex-wrap items-center gap-2.5"><Status status={idea.status} /><span className="text-xs text-dim">{idea.author}</span></div>
            <p className="mt-2 whitespace-pre-wrap text-[14.5px] leading-relaxed">{idea.text}</p>
            {declined[idea.id] && <p className="mt-2 text-sm text-caution">{t('idea.declined')} {declined[idea.id]}</p>}
            <div className="mt-3 flex flex-wrap gap-2.5">
              {idea.status === 'new' && aiReady && (
                <button type="button" disabled={drafting !== null} onClick={() => void draft(idea)}
                  className="flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold disabled:opacity-50"
                  style={{ color: '#d8b4fe', background: 'rgb(139 92 246 / .14)', border: '1px solid rgb(139 92 246 / .45)' }}>
                  <SparkIcon size={16} />{drafting === idea.id ? t('idea.drafting') : t('idea.draft')}
                </button>
              )}
              {idea.proposal_id && idea.status === 'drafted' && (
                <button type="button" onClick={() => onOpenReview(idea.proposal_id!)} className="rounded-xl border border-line-strong px-3.5 py-2 text-sm text-ink hover:bg-white/[.04]">{t('idea.viewReview')}</button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ReviewsTab({ detail, reviewId, setReviewId, onChange, onError, onNotice }: TabProps & { reviewId: string | null; setReviewId: (id: string | null) => void }) {
  const { t, lang } = useLang()
  const [view, setView] = useState<ProposalView | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!reviewId) { setView(null); return }
    let live = true
    getProposal(detail.id, reviewId, lang).then((v) => live && setView(v)).catch((e) => live && onError(message(e)))
    return () => { live = false }
  }, [detail.id, reviewId, lang, detail.proposals, onError])

  const act = async (fn: () => Promise<unknown>, done: string) => {
    setBusy(true)
    onError(null)
    try {
      await fn()
      onNotice(done)
    } catch (e) { onError(message(e)) } finally {
      setBusy(false)
      await onChange()
    }
  }

  const canUndo = detail.history.some((h) => !h.undone)
  return (
    <div className="grid h-full min-h-0 gap-4 md:grid-cols-[300px_1fr]">
      <aside className="scroll min-h-0 overflow-y-auto pr-1">
        <ul className="grid gap-2" aria-label={t('proj.reviewsTab')}>
          {detail.proposals.length === 0 && <li className="py-6 text-center text-sm text-muted">{t('rev.none')}</li>}
          {detail.proposals.map((p) => (
            <li key={p.id}>
              <button type="button" onClick={() => setReviewId(p.id)} aria-current={reviewId === p.id} data-testid="proposal-item"
                className="glass w-full rounded-2xl px-4 py-3 text-left transition hover:bg-white/[.04]"
                style={reviewId === p.id ? { borderColor: 'rgb(34 211 238 / .5)' } : undefined}>
                <Status status={p.status} />
                <p className="mt-1.5 line-clamp-2 text-sm">{p.summary}</p>
                <p className="mt-1 font-mono text-[11px] text-dim">{p.files.length} {t('rev.files')}{p.warnings > 0 && ` · ⚠ ${p.warnings}`}</p>
              </button>
            </li>
          ))}
        </ul>
        <section className="mt-6">
          <h2 className="mb-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('rev.history')}</h2>
          {detail.history.length === 0 ? <p className="text-sm text-dim">{t('rev.noHistory')}</p> : (
            <ul className="grid gap-1.5 text-xs text-muted">
              {detail.history.map((h) => (
                <li key={h.seq} className="flex items-center justify-between gap-2" style={{ opacity: h.undone ? 0.5 : 1 }}>
                  <span className="truncate">#{h.seq} · {h.files.join(', ')}</span>{h.undone && <span>{t('status.reverted')}</span>}
                </li>
              ))}
            </ul>
          )}
          <button type="button" disabled={!canUndo || busy} onClick={() => void act(() => undoLast(detail.id), t('rev.reverted'))}
            className="mt-3 rounded-xl border border-line-strong px-3.5 py-2 text-sm text-muted hover:text-ink disabled:opacity-40">{t('rev.undo')}</button>
        </section>
      </aside>

      <div className="scroll min-h-0 overflow-y-auto pb-6 pr-2" data-testid="review-panel">
        {!view ? <p className="py-16 text-center text-sm text-muted">{t('rev.pick')}</p> : (
          <div className="grid gap-4">
            <header className="glass rounded-2xl p-5">
              <Status status={view.status} />
              <p className="mt-2 text-[15px] leading-relaxed">{view.summary}</p>
              <p className="mt-2 text-xs text-dim">{t('rev.explain')}</p>
            </header>
            {view.warnings.length > 0 && (
              <section className="rounded-2xl border border-[#ff7a45]/40 bg-[#ff7a45]/10 p-4" role="alert" data-testid="warnings">
                <h3 className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#ff9b6b]">{t('rev.warnings')}</h3>
                <ul className="mt-2 grid list-disc gap-1 pl-5 text-sm">{view.warnings.map((w) => <li key={w.id}>{w.text}</li>)}</ul>
              </section>
            )}
            {view.changes.map((c) => <DiffView key={c.path} change={c} />)}
            {view.status === 'open' && (
              <div className="flex gap-3">
                <button type="button" disabled={busy} onClick={() => void act(() => approveProposal(detail.id, view.id), t('rev.applied'))}
                  className="rounded-xl px-5 py-2.5 text-sm font-semibold text-bg disabled:opacity-50" style={{ background: '#34d399' }}>{t('rev.approve')}</button>
                <button type="button" disabled={busy} onClick={() => void act(() => rejectProposal(detail.id, view.id), '')}
                  className="rounded-xl border border-line-strong px-5 py-2.5 text-sm text-muted hover:text-ink disabled:opacity-50">{t('rev.reject')}</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
