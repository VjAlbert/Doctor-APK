import { explainReport, previewExplanation } from '../lib/ai'
import { useLang } from '../lib/lang'
import type { Report } from '../lib/types'
import { AiAnswerPanel } from './AiAnswerPanel'

/** Plain-language explanation of an analysis report. */
export function ExplainPanel({ report }: { report: Report }) {
  const { lang } = useLang()
  return (
    <AiAnswerPanel
      ask={() => explainReport(report, lang)}
      preview={() => previewExplanation(report, lang)}
      resetKey={`${report.file.sha256}-${lang}`}
      buttonLabel="ai.explain"
      title="ai.result"
    />
  )
}
