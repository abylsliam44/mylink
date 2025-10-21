interface Education {
  place: string
  degree: string
  start: string
  end: string
}

interface EducationInputProps {
  educations: Education[]
  onChange: (educations: Education[]) => void
  className?: string
}

export default function EducationInput({ educations, onChange, className = '' }: EducationInputProps) {
  const addEducation = () => {
    onChange([...educations, { place: '', degree: '', start: '', end: '' }])
  }

  const updateEducation = (index: number, field: keyof Education, value: string) => {
    const updated = educations.map((edu, i) => 
      i === index ? { ...edu, [field]: value } : edu
    )
    onChange(updated)
  }

  const removeEducation = (index: number) => {
    onChange(educations.filter((_, i) => i !== index))
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Образование</h3>
        <button
          onClick={addEducation}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Добавить образование
        </button>
      </div>

      {educations.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.083 12.083 0 01.665-6.479L12 14z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Нет образования</h3>
          <p className="mt-1 text-sm text-gray-500">Добавьте информацию об образовании</p>
        </div>
      ) : (
        <div className="space-y-4">
          {educations.map((edu, index) => (
            <div key={index} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <h4 className="text-md font-medium text-gray-900">
                  Образование #{index + 1}
                </h4>
                <button
                  onClick={() => removeEducation(index)}
                  className="text-red-600 hover:text-red-800 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Учебное заведение *
                  </label>
                  <input
                    type="text"
                    value={edu.place}
                    onChange={(e) => updateEducation(index, 'place', e.target.value)}
                    placeholder="Название университета, колледжа"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Степень/Специальность *
                  </label>
                  <select
                    value={edu.degree}
                    onChange={(e) => updateEducation(index, 'degree', e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="">Выберите степень</option>
                    <option value="Среднее образование">Среднее образование</option>
                    <option value="Среднее специальное">Среднее специальное</option>
                    <option value="Бакалавр">Бакалавр</option>
                    <option value="Специалист">Специалист</option>
                    <option value="Магистр">Магистр</option>
                    <option value="Кандидат наук">Кандидат наук</option>
                    <option value="Доктор наук">Доктор наук</option>
                    <option value="MBA">MBA</option>
                    <option value="Другое">Другое</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Год поступления
                  </label>
                  <input
                    type="number"
                    value={edu.start}
                    onChange={(e) => updateEducation(index, 'start', e.target.value)}
                    placeholder="2020"
                    min="1950"
                    max="2030"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Год окончания
                  </label>
                  <input
                    type="number"
                    value={edu.end}
                    onChange={(e) => updateEducation(index, 'end', e.target.value)}
                    placeholder="2024"
                    min="1950"
                    max="2030"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
