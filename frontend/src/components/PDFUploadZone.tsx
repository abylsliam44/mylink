import { useState, useRef } from 'react'
import LoadingSpinner from './LoadingSpinner'

interface PDFUploadZoneProps {
  onFileSelect: (file: File) => void
  onUpload: () => void
  isUploading: boolean
  selectedFile: File | null
  className?: string
}

export default function PDFUploadZone({ 
  onFileSelect, 
  onUpload, 
  isUploading, 
  selectedFile, 
  className = '' 
}: PDFUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = Array.from(e.dataTransfer.files)
    const pdfFile = files.find(file => file.type === 'application/pdf')
    
    if (pdfFile) {
      onFileSelect(pdfFile)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type === 'application/pdf') {
      onFileSelect(file)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Upload Zone */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer ${
          isDragOver
            ? 'border-blue-500 bg-blue-50'
            : selectedFile
            ? 'border-green-500 bg-green-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <div className="space-y-4">
          {/* Icon */}
          <div className="mx-auto w-16 h-16 flex items-center justify-center">
            {isUploading ? (
              <LoadingSpinner size="lg" />
            ) : selectedFile ? (
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            ) : (
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
            )}
          </div>

          {/* Text */}
          <div>
            {selectedFile ? (
              <div>
                <h3 className="text-lg font-semibold text-green-700 mb-2">PDF выбран</h3>
                <p className="text-sm text-green-600 mb-2">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
              </div>
            ) : (
              <div>
                <h3 className="text-lg font-semibold text-gray-700 mb-2">
                  {isDragOver ? 'Отпустите файл здесь' : 'Загрузите PDF резюме'}
                </h3>
                <p className="text-sm text-gray-500 mb-2">
                  Перетащите файл сюда или нажмите для выбора
                </p>
                <p className="text-xs text-gray-400">
                  Поддерживается только PDF формат, до 10 МБ
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Upload Button */}
      {selectedFile && (
        <div className="flex justify-center">
          <button
            onClick={onUpload}
            disabled={isUploading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isUploading ? <LoadingSpinner size="sm" /> : null}
            {isUploading ? 'Загрузка...' : 'Загрузить PDF'}
          </button>
        </div>
      )}
    </div>
  )
}
