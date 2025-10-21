import { useState, useCallback } from 'react'
import type { NotificationType } from '../components/Notification'

interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  duration?: number
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  const addNotification = useCallback((
    type: NotificationType,
    title: string,
    message: string,
    duration?: number
  ) => {
    const id = Math.random().toString(36).substr(2, 9)
    setNotifications(prev => [...prev, { id, type, title, message, duration }])
  }, [])

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }, [])

  const showSuccess = useCallback((title: string, message: string, duration?: number) => {
    addNotification('success', title, message, duration)
  }, [addNotification])

  const showError = useCallback((title: string, message: string, duration?: number) => {
    addNotification('error', title, message, duration)
  }, [addNotification])

  const showWarning = useCallback((title: string, message: string, duration?: number) => {
    addNotification('warning', title, message, duration)
  }, [addNotification])

  const showInfo = useCallback((title: string, message: string, duration?: number) => {
    addNotification('info', title, message, duration)
  }, [addNotification])

  return {
    notifications,
    addNotification,
    removeNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}
