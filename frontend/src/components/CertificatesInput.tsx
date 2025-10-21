interface Certificate {
  name: string
  issuer: string
  year: string
}

interface CertificatesInputProps {
  certificates: Certificate[]
  onChange: (certificates: Certificate[]) => void
  className?: string
}

export default function CertificatesInput({ certificates, onChange, className = '' }: CertificatesInputProps) {
  const addCertificate = () => {
    onChange([...certificates, { name: '', issuer: '', year: '' }])
  }

  const updateCertificate = (index: number, field: keyof Certificate, value: string) => {
    const updated = certificates.map((cert, i) => 
      i === index ? { ...cert, [field]: value } : cert
    )
    onChange(updated)
  }

  const removeCertificate = (index: number) => {
    onChange(certificates.filter((_, i) => i !== index))
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Сертификаты и курсы</h3>
        <button
          onClick={addCertificate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Добавить сертификат
        </button>
      </div>

      {certificates.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Нет сертификатов</h3>
          <p className="mt-1 text-sm text-gray-500">Добавьте ваши сертификаты и пройденные курсы</p>
        </div>
      ) : (
        <div className="space-y-4">
          {certificates.map((cert, index) => (
            <div key={index} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <h4 className="text-md font-medium text-gray-900">
                  Сертификат #{index + 1}
                </h4>
                <button
                  onClick={() => removeCertificate(index)}
                  className="text-red-600 hover:text-red-800 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Название сертификата *
                  </label>
                  <input
                    type="text"
                    value={cert.name}
                    onChange={(e) => updateCertificate(index, 'name', e.target.value)}
                    placeholder="AWS Certified Solutions Architect"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Организация *
                  </label>
                  <input
                    type="text"
                    value={cert.issuer}
                    onChange={(e) => updateCertificate(index, 'issuer', e.target.value)}
                    placeholder="Amazon Web Services"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Год получения
                  </label>
                  <input
                    type="number"
                    value={cert.year}
                    onChange={(e) => updateCertificate(index, 'year', e.target.value)}
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

      {/* Popular certificates suggestions */}
      {certificates.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 mb-3">Популярные сертификаты:</h4>
          <div className="flex flex-wrap gap-2">
            {[
              'AWS Certified Solutions Architect',
              'Google Cloud Professional',
              'Microsoft Azure Fundamentals',
              'Cisco CCNA',
              'PMP (Project Management)',
              'ITIL Foundation',
              'CompTIA Security+',
              'Certified Kubernetes Administrator'
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => {
                  const newCert = { name: suggestion, issuer: '', year: '' }
                  onChange([...certificates, newCert])
                }}
                className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
