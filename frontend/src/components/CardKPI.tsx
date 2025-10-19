import React from 'react'

type Props = {
  icon?: React.ReactNode
  title: string
  value: string | number
  delta?: number | null
  toneByValue?: boolean // when true and value is % number, colorize icon bg and show emoji
}

export function CardKPI({ icon, title, value, delta = null, toneByValue = false }: Props) {
  const deltaSign = typeof delta === 'number' ? (delta > 0 ? '+' : '') : ''
  const deltaColor = typeof delta === 'number' ? (delta >= 0 ? 'text-green-600' : 'text-red-600') : 'text-grayx-500'
  const pct = typeof value === 'string' && value.toString().endsWith('%') ? Number(String(value).replace('%','')) : (typeof value === 'number' ? Number(value) : NaN)
  const tone = toneByValue && !Number.isNaN(pct)
  const color = !tone ? '#EEF2FF' : (pct > 50 ? '#EAF7EE' : pct >= 31 ? '#FFF7E6' : '#FDECEC')
  const fg = !tone ? '#4F46E5' : (pct > 50 ? '#16A34A' : pct >= 31 ? '#F59E0B' : '#DC2626')
  const emoji = !tone ? null : (pct > 50 ? '✅' : pct >= 31 ? '⚠️' : '⛔️')
  return (
    <div className="rounded-2xl border border-[#E6E8EB] bg-white shadow-sm p-4 flex items-center gap-3">
      <div aria-hidden className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: color, color: fg }}>
        {emoji || icon}
      </div>
      <div className="min-w-0">
        <div className="text-[12px] leading-[18px] text-[#666] truncate">{title}</div>
        <div className="flex items-baseline gap-2">
          <div className="text-[24px] leading-[28px] font-semibold text-[#0A0A0A]">{value}</div>
          {delta !== null && (
            <span className={`text-[12px] leading-[18px] ${deltaColor}`}>{deltaSign}{delta}%</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default CardKPI


