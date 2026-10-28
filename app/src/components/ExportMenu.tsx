import { useLang } from '../lib/lang'
import { buildReportHtml, reportFileName } from '../lib/reportHtml'
import type { Report } from '../lib/types'
import { DownloadIcon, PrinterIcon } from './Icons'

function download(name: string, html: string) {
  const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Prints through a hidden frame so the app UI itself is never in the printout. */
function print(html: string) {
  const frame = document.createElement('iframe')
  frame.setAttribute('aria-hidden', 'true')
  frame.style.cssText = 'position:fixed;width:0;height:0;border:0;visibility:hidden'
  frame.srcdoc = html
  frame.onload = () => {
    frame.contentWindow?.focus()
    frame.contentWindow?.print()
    setTimeout(() => frame.remove(), 2000)
  }
  document.body.append(frame)
}

export function ExportMenu({ report }: { report: Report }) {
  const { t, lang } = useLang()
  const button = 'flex items-center gap-2 rounded-xl border border-line-strong px-3.5 py-2 text-sm text-muted transition hover:text-ink'
  return (
    <div className="flex gap-2" aria-label={t('export.label')} role="group">
      <button type="button" className={button} onClick={() => download(reportFileName(report), buildReportHtml(report, lang))}>
        <DownloadIcon size={16} />{t('export.html')}
      </button>
      <button type="button" className={button} onClick={() => print(buildReportHtml(report, lang))}>
        <PrinterIcon size={16} />{t('export.print')}
      </button>
    </div>
  )
}
