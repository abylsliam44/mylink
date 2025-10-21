import { useEffect, useState } from 'react'

interface PageLoaderProps {
  show: boolean
  message?: string
}

export default function PageLoader({ show, message = 'Загрузка...' }: PageLoaderProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (show) {
      setIsVisible(true)
    } else {
      const timer = setTimeout(() => setIsVisible(false), 300)
      return () => clearTimeout(timer)
    }
  }, [show])

  if (!isVisible) return null

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm transition-opacity duration-300 ${
      show ? 'opacity-100' : 'opacity-0'
    }`}>
      <div className="bg-white rounded-2xl p-8 shadow-2xl max-w-sm w-full mx-4">
        {/* Animated Logo/Icon */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            {/* Outer ring */}
            <div className="w-16 h-16 border-4 border-blue-100 rounded-full animate-spin">
              <div className="absolute top-0 left-0 w-full h-full border-4 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
            </div>
            
            {/* Inner pulse */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 bg-blue-600 rounded-full animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Message */}
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">SmartBot</h3>
          <p className="text-gray-600 animate-pulse">{message}</p>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center mt-6 space-x-2">
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    </div>
  )
}
