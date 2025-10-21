import Notification from './Notification'

interface NotificationType {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
}

interface NotificationContainerProps {
  notifications: NotificationType[]
  onRemove: (id: string) => void
}

export default function NotificationContainer({ 
  notifications, 
  onRemove 
}: NotificationContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {notifications.map((notification, index) => (
        <div
          key={notification.id}
          className="transform transition-all duration-300 ease-in-out"
          style={{
            transform: `translateY(${index * 10}px)`,
            zIndex: 1000 - index
          }}
        >
          <Notification
            type={notification.type}
            title={notification.title}
            message={notification.message}
            duration={notification.duration}
            onClose={() => onRemove(notification.id)}
            show={true}
          />
        </div>
      ))}
    </div>
  )
}
