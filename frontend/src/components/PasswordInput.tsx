import { useState } from 'react'
import { useLanguage } from '../lib/LanguageContext'
import { EyeIcon, EyeOffIcon } from './icons'

interface PasswordInputProps {
  id: string
  value: string
  onChange: (value: string) => void
  autoComplete?: string
  required?: boolean
  minLength?: number
  placeholder?: string
}

export function PasswordInput({ id, value, onChange, autoComplete, required, minLength, placeholder }: PasswordInputProps) {
  const { t } = useLanguage()
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="password-field">
      <input
        id={id}
        type={isVisible ? 'text' : 'password'}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        required={required}
        minLength={minLength}
        placeholder={placeholder}
      />
      <button
        type="button"
        className="password-toggle-btn"
        onClick={() => setIsVisible((prev) => !prev)}
        aria-label={isVisible ? t('passwordHide') : t('passwordShow')}
      >
        {isVisible ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  )
}
