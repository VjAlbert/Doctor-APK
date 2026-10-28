import { motion } from 'framer-motion'
import { useCallback, useRef, useState, type DragEvent } from 'react'
import { useLang } from '../lib/lang'
import { UploadIcon } from './Icons'

export function DropZone({ onFile }: { onFile: (file: File) => void }) {
  const { t } = useLang()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const depth = useRef(0) // dragenter/leave fire for every child element

  const pick = useCallback((files: FileList | null) => {
    const file = files?.[0]
    if (file) onFile(file)
  }, [onFile])

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    depth.current = 0
    setDragging(false)
    pick(event.dataTransfer.files)
  }

  return (
    <motion.button
      type="button"
      onClick={() => input.current?.click()}
      onDragEnter={(e) => { e.preventDefault(); depth.current += 1; setDragging(true) }}
      onDragLeave={() => { depth.current -= 1; if (depth.current <= 0) setDragging(false) }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      animate={{ scale: dragging ? 1.02 : 1 }}
      whileHover={{ y: -2 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className="drop-ring group relative flex w-full cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl px-8 py-14 text-center"
      style={{ boxShadow: dragging ? '0 0 80px -10px rgb(34 211 238 / .55)' : '0 30px 60px -30px rgb(0 0 0 / .7)' }}
    >
      <span className="relative grid size-20 place-items-center rounded-full text-cyan"
        style={{ background: 'radial-gradient(circle, rgb(34 211 238 / .22), rgb(34 211 238 / .04) 70%)',
                 border: '1px solid rgb(34 211 238 / .4)' }}>
        <motion.span animate={{ y: dragging ? [-2, 3, -2] : 0 }} transition={{ repeat: dragging ? Infinity : 0, duration: 0.9 }}>
          <UploadIcon size={34} />
        </motion.span>
      </span>
      <span className="text-xl font-semibold tracking-tight">
        {dragging ? t('home.dropActive') : t('home.drop')}
      </span>
      <span className="text-sm text-muted">{t('home.browse')}</span>
      <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-dim">{t('home.formats')}</span>
      <input ref={input} type="file" hidden accept=".apk,.xapk,.apkm,application/vnd.android.package-archive"
        data-testid="file-input"
        onChange={(e) => { pick(e.target.files); e.target.value = '' }} />
    </motion.button>
  )
}
