interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
  className?: string
}

export default function LoadingSpinner({ 
  size = 'md', 
  text, 
  className = '' 
}: LoadingSpinnerProps) {
  const getSize = () => {
    switch (size) {
      case 'sm': return 'w-4 h-4'
      case 'md': return 'w-8 h-8'
      case 'lg': return 'w-12 h-12'
    }
  }

  return (
    <div className={`flex flex-col items-center justify-center space-y-2 ${className}`}>
      <div className={`${getSize()} relative`}>
        {/* Outer ring */}
        <div className={`${getSize()} border-2 border-gray-200 rounded-full animate-spin`}>
          <div className="absolute top-0 left-0 w-full h-full border-2 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
        </div>
        
        {/* Inner pulse */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-1/2 h-1/2 bg-blue-600 rounded-full animate-pulse opacity-60"></div>
        </div>
      </div>
      
      {text && (
        <p className="text-sm text-gray-600 animate-pulse">{text}</p>
      )}
    </div>
  )
}
