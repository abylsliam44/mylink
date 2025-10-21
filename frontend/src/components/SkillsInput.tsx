import { useState } from 'react'

interface SkillsInputProps {
  skills: string[]
  onChange: (skills: string[]) => void
  className?: string
}

export default function SkillsInput({ skills, onChange, className = '' }: SkillsInputProps) {
  const [newSkill, setNewSkill] = useState('')

  const addSkill = () => {
    if (newSkill.trim() && !skills.includes(newSkill.trim())) {
      onChange([...skills, newSkill.trim()])
      setNewSkill('')
    }
  }

  const removeSkill = (index: number) => {
    onChange(skills.filter((_, i) => i !== index))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addSkill()
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Навыки и технологии
        </label>
        
        {/* Add new skill */}
        <div className="flex gap-2">
          <input
            type="text"
            value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Введите навык (например: React, Python, SQL)"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <button
            onClick={addSkill}
            disabled={!newSkill.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Добавить
          </button>
        </div>
      </div>

      {/* Skills list */}
      {skills.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-600">Добавленные навыки:</p>
          <div className="flex flex-wrap gap-2">
            {skills.map((skill, index) => (
              <div
                key={index}
                className="flex items-center gap-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
              >
                <span>{skill}</span>
                <button
                  onClick={() => removeSkill(index)}
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggestions */}
      <div className="space-y-2">
        <p className="text-sm text-gray-600">Популярные навыки:</p>
        <div className="flex flex-wrap gap-2">
          {[
            'JavaScript', 'Python', 'React', 'Node.js', 'SQL', 'Git', 'Docker',
            'TypeScript', 'Vue.js', 'Angular', 'Java', 'C#', 'PHP', 'Go',
            'AWS', 'Azure', 'MongoDB', 'PostgreSQL', 'Redis', 'Kubernetes'
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                if (!skills.includes(suggestion)) {
                  onChange([...skills, suggestion])
                }
              }}
              disabled={skills.includes(suggestion)}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
