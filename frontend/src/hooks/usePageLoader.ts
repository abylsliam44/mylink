import { useState, useCallback } from 'react'

export function usePageLoader() {
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('Загрузка...')

  const startLoading = useCallback((message?: string) => {
    setLoadingMessage(message || 'Загрузка...')
    setIsLoading(true)
  }, [])

  const stopLoading = useCallback(() => {
    setIsLoading(false)
  }, [])

  const withLoading = useCallback(async <T>(
    asyncFn: () => Promise<T>,
    message?: string
  ): Promise<T> => {
    try {
      startLoading(message)
      const result = await asyncFn()
      return result
    } finally {
      stopLoading()
    }
  }, [startLoading, stopLoading])

  return {
    isLoading,
    loadingMessage,
    startLoading,
    stopLoading,
    withLoading
  }
}
