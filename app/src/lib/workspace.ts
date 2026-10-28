import { engineBase, EngineError } from './client'
import { engineRequest } from './http'
import type { Lang, Report } from './types'

export interface ProjectSummary {
  id: string
  name: string
  package: string
  created: string
  open_ideas: number
  open_proposals: number
}

export type IdeaStatus = 'new' | 'drafted' | 'accepted' | 'rejected'

export interface Idea {
  id: string
  text: string
  author: string
  created: string
  status: IdeaStatus
  proposal_id: string | null
}

export interface ProposalBrief {
  id: string
  idea_id: string
  status: 'open' | 'approved' | 'rejected' | 'stale' | 'reverted'
  created: string
  summary: string
  files: string[]
  warnings: number
}

export interface HistoryItem {
  seq: number
  proposal_id: string
  at: string
  files: string[]
  undone: boolean
}

export interface ProjectDetail extends ProjectSummary {
  files: { path: string; size: number }[]
  ideas: Idea[]
  proposals: ProposalBrief[]
  history: HistoryItem[]
}

export interface FileChange {
  path: string
  is_new: boolean
  diff: string[]
  truncated: boolean
  added: number
  removed: number
}

export interface ProposalView {
  id: string
  idea_id: string
  status: ProposalBrief['status']
  created: string
  summary: string
  warnings: { id: string; items: string[]; text: string }[]
  changes: FileChange[]
}

export interface DraftResult {
  proposal: ProposalView | null
  summary: string
  declined: boolean
}

const post = <T>(path: string, body: unknown = {}) =>
  engineRequest<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const listProjects = () => engineRequest<{ projects: ProjectSummary[] }>('/workspaces').then((r) => r.projects)

export const createProject = (input: {
  report: Report
  codeId?: string
  name: string
  lang: Lang
  ownerConfirmed: boolean
  useAi: boolean
}) =>
  post<ProjectSummary & { spec: 'ai' | 'template' }>('/workspaces', {
    report: input.report, code_id: input.codeId, name: input.name, lang: input.lang,
    owner_confirmed: input.ownerConfirmed, use_ai: input.useAi,
  })

export const getProject = (id: string) => engineRequest<ProjectDetail>(`/workspaces/${id}`)
export const readProjectFile = (id: string, path: string) =>
  engineRequest<{ path: string; content: string }>(`/workspaces/${id}/file?path=${encodeURIComponent(path)}`).then((r) => r.content)
export const addIdea = (id: string, text: string, author: string) => post<Idea>(`/workspaces/${id}/ideas`, { text, author })
export const draftIdea = (id: string, ideaId: string, lang: Lang) => post<DraftResult>(`/workspaces/${id}/ideas/${ideaId}/draft`, { lang })
export const getProposal = (id: string, proposalId: string, lang: Lang) =>
  engineRequest<ProposalView>(`/workspaces/${id}/proposals/${proposalId}?lang=${lang}`)
export const approveProposal = (id: string, proposalId: string) => post<{ status: string }>(`/workspaces/${id}/proposals/${proposalId}/approve`)
export const rejectProposal = (id: string, proposalId: string) => post<{ status: string }>(`/workspaces/${id}/proposals/${proposalId}/reject`)
export const undoLast = (id: string) => post<{ reverted: string[] }>(`/workspaces/${id}/undo`)
export const exportIdeas = (id: string) => engineRequest<unknown>(`/workspaces/${id}/ideas/export`)
export const importIdeas = (id: string, data: unknown) => post<{ added: number; skipped: number }>(`/workspaces/${id}/ideas/import`, data)

/** Downloads the project's files as a zip, through the local engine. */
export async function downloadProjectZip(id: string): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${await engineBase()}/workspaces/${id}/export.zip`)
  } catch {
    throw new EngineError('engine_unreachable', 'The analysis engine is not running.')
  }
  if (!response.ok) throw new EngineError('failed', `Engine answered with status ${response.status}.`)
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `${id}.zip`
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export const STATUS_COLOR: Record<string, string> = {
  new: '#8a9bb2', drafted: '#a78bfa', accepted: '#34d399', rejected: '#ff5c5c',
  open: '#fbbf24', approved: '#34d399', stale: '#ff7a45', reverted: '#8a9bb2',
}

/** Classifies one line of a unified diff for display. */
export function diffLineKind(line: string): 'add' | 'del' | 'hunk' | 'meta' | 'ctx' {
  if (line.startsWith('+++') || line.startsWith('---')) return 'meta'
  if (line.startsWith('@@')) return 'hunk'
  if (line.startsWith('+')) return 'add'
  if (line.startsWith('-')) return 'del'
  return 'ctx'
}
