import { ShieldIcon } from './Icons'

export function Logo() {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <span className="grid size-9 place-items-center rounded-xl text-cyan"
        style={{ background: 'linear-gradient(145deg, rgb(34 211 238 / .18), rgb(139 92 246 / .12))',
                 border: '1px solid rgb(34 211 238 / .35)', boxShadow: '0 0 24px -4px rgb(34 211 238 / .5)' }}>
        <ShieldIcon size={20} />
      </span>
      <span className="text-[17px] font-semibold tracking-tight">
        APK<span className="text-cyan">Guard</span>
      </span>
    </div>
  )
}
