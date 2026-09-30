import { useId } from 'react'

export function Field({ label, note, invalid = false, ...input }) {
  const id = useId()
  const noteId = `${id}-note`
  return (
    <label className={`field ${invalid ? 'field-invalid' : ''}`} htmlFor={id}>
      <span className="field-label">{label}</span>
      <input
        id={id}
        className="field-input"
        aria-describedby={note ? noteId : undefined}
        aria-invalid={invalid || undefined}
        {...input}
      />
      {note ? (
        <span id={noteId} className={`field-note ${invalid ? 'field-error' : ''}`}>
          {note}
        </span>
      ) : null}
    </label>
  )
}
