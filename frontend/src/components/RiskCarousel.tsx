import { useEffect, useMemo, useRef, useState } from 'react'

type Props = {
  items: string[]
  intervalMs?: number
}

export default function RiskCarousel({ items, intervalMs = 2800 }: Props) {
  const safeItems = useMemo(() => (items || []).filter(Boolean), [items])
  const [idx, setIdx] = useState(0)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (safeItems.length <= 1) return
    timer.current && window.clearInterval(timer.current)
    timer.current = window.setInterval(() => {
      setIdx((p) => (p + 1) % safeItems.length)
    }, intervalMs)
    return () => { if (timer.current) window.clearInterval(timer.current) }
  }, [safeItems, intervalMs])

  if (safeItems.length === 0) {
    return <div className="text-[12px] text-[#666]">Зоны риска ожидают данные</div>
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-[#E6E8EB]">
      <div className="min-h-[96px] p-4 bg-white">
        <div className="transition-all duration-500 ease-out" key={idx}>
          <div className="text-[13px] leading-[18px]">{safeItems[idx]}</div>
        </div>
      </div>
      {safeItems.length > 1 && (
        <div className="absolute bottom-2 left-0 right-0 flex items-center justify-center gap-1">
          {safeItems.map((_, i) => (
            <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === idx ? 'bg-[#4F46E5]' : 'bg-[#E6E8EB]'}`} />
          ))}
        </div>
      )}
    </div>
  )
}


