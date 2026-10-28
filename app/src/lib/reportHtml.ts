import { formatSize } from './format'
import { SEVERITY_COLOR, LEVEL_COLOR } from './severity'
import { translate, severityKey } from './ui'
import type { Finding, Lang, Report } from './types'

/** Escapes text for HTML. Every string from the APK (names, URLs) goes through this. */
export function esc(value: unknown): string {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const STYLE = `
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 40px; font: 14px/1.55 -apple-system, "Segoe UI", Inter, Roboto, sans-serif; color: #17202e; background: #fff; }
  .page { max-width: 820px; margin: 0 auto; }
  h1 { font-size: 26px; margin: 0 0 4px; } h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .08em; color: #5b6b82; margin: 32px 0 10px; border-bottom: 1px solid #dde4ee; padding-bottom: 6px; }
  .sub { color: #5b6b82; margin: 0; font-size: 13px; }
  .verdict { display: flex; gap: 20px; align-items: center; margin: 22px 0; padding: 18px 20px; border-radius: 12px; border: 1px solid #dde4ee; }
  .score { font: 700 44px/1 ui-monospace, Menlo, monospace; min-width: 84px; text-align: center; }
  .verdict h3 { margin: 0 0 4px; font-size: 20px; } .verdict p { margin: 0; color: #43536b; }
  table { width: 100%; border-collapse: collapse; } td, th { text-align: left; padding: 6px 8px; vertical-align: top; border-bottom: 1px solid #eef2f7; }
  th { width: 28%; color: #5b6b82; font-weight: 500; } code, .mono { font: 12px ui-monospace, Menlo, monospace; word-break: break-all; }
  .finding { border: 1px solid #dde4ee; border-left-width: 4px; border-radius: 8px; padding: 10px 14px; margin: 0 0 10px; break-inside: avoid; }
  .finding h4 { margin: 0 0 2px; font-size: 14px; } .finding p { margin: 4px 0 0; color: #43536b; }
  .badge { font: 600 10.5px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .06em; padding: 1px 8px; border-radius: 99px; color: #fff; }
  .note { margin-top: 28px; padding: 12px 14px; background: #f4f7fb; border-radius: 8px; color: #43536b; font-size: 12.5px; }
  @media print { body { padding: 0; } h2 { break-after: avoid; } }
`

function findingHtml(f: Finding, lang: Lang): string {
  const color = SEVERITY_COLOR[f.severity]
  const advice = f.text.advice ? `<p><strong>${esc(translate(lang, 'threats.advice'))}:</strong> ${esc(f.text.advice)}</p>` : ''
  const note = f.text.note ? `<p><em>${esc(f.text.note)}</em></p>` : ''
  return `<div class="finding" style="border-left-color:${color}">
    <span class="badge" style="background:${color}">${esc(translate(lang, severityKey(f.severity)))}</span>
    <h4>${esc(f.text.title)}</h4><p>${esc(f.text.description)}</p>${note}${advice}</div>`
}

/** A self-contained, printer-friendly report. It has no scripts and no external resources. */
export function buildReportHtml(report: Report, lang: Lang, generatedAt = new Date()): string {
  const t = (key: Parameters<typeof translate>[1]) => esc(translate(lang, key))
  const { verdict, app, file } = report
  const color = LEVEL_COLOR[verdict.level]
  const shown = report.findings.filter((f) => f.severity !== 'info')
  const date = new Intl.DateTimeFormat(lang, { dateStyle: 'long', timeStyle: 'short' }).format(generatedAt)

  const facts: [string, string][] = [
    [t('verdict.package'), esc(app.package)],
    [t('verdict.version'), esc(app.version_name ?? '—')],
    [t('verdict.category'), esc(verdict.text.category)],
    [t('verdict.signature'), esc(report.authenticity.label)],
    [t('verdict.size'), esc(formatSize(file.size))],
    ['SHA-256', `<span class="mono">${esc(file.sha256)}</span>`],
  ]
  const certs = report.certificates
    .map((c) => `<tr><th>${t('sig.subject')}</th><td>${esc(c.subject)}</td></tr>
      <tr><th>${t('sig.issuer')}</th><td>${esc(c.issuer)}</td></tr>
      <tr><th>SHA-256</th><td class="mono">${esc(c.sha256)}</td></tr>`)
    .join('')

  return `<!doctype html>
<html lang="${lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>APKGuard - ${esc(app.name || file.name)}</title><style>${STYLE}</style></head>
<body><div class="page">
  <p class="sub">APKGuard · ${esc(date)}</p>
  <h1>${esc(app.name || file.name)}</h1>
  <p class="sub">${esc(file.name)}</p>
  <div class="verdict" style="border-color:${color}66;background:${color}12">
    <div class="score" style="color:${color}">${verdict.score}</div>
    <div><h3 style="color:${color}">${esc(verdict.text.title)}</h3><p>${esc(verdict.text.summary)}</p></div>
  </div>
  <h2>${t('threats.title')}</h2>
  ${shown.length ? shown.map((f) => findingHtml(f, lang)).join('') : `<p>${t('verdict.nothing')}</p>`}
  <h2>${t('perm.title')} (${report.permissions.length})</h2>
  <table>${report.permissions.map((p) => `<tr><td class="mono">${esc(p)}</td></tr>`).join('')}</table>
  <h2>${t('sig.certificates')}</h2>
  <table>${certs || `<tr><td>${t('sig.explain.unsigned')}</td></tr>`}</table>
  <h2>${t('tab.summary')}</h2>
  <table>${facts.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('')}</table>
  <div class="note">${esc(verdict.text.limitations)}</div>
  <p class="sub" style="margin-top:14px">APKGuard${report.engine ? ` ${esc(report.engine.version)} (${esc(report.engine.build)})` : ''}</p>
</div></body></html>`
}

/** Safe file name for the saved report. */
export function reportFileName(report: Report): string {
  const base = (report.app.package || report.file.name).replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 60)
  return `apkguard-${base}.html`
}
