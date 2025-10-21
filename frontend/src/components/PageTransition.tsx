import { useEffect, useState } from 'react'

interface PageTransitionProps {
  children: React.ReactNode
  className?: string
}

export default function PageTransition({ children, className = '' }: PageTransitionProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    // Trigger animation on mount
    const timer = setTimeout(() => setIsVisible(true), 50)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className={`transition-all duration-500 ease-out ${
      isVisible 
        ? 'opacity-100 translate-y-0' 
        : 'opacity-0 translate-y-4'
    } ${className}`}>
      {children}
    </div>
  )
}
