import { useEffect, useRef } from 'react'

/* Deleting is the one action in the app that cannot be taken back, which is
   why it is also one of the only places red appears. */

export function DeleteDialog({ message, onCancel, onConfirm }) {
  const cancelRef = useRef(null)

  useEffect(() => {
    cancelRef.current?.focus()
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onCancel])

  return (
    <div
      className="scrim"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel()
      }}
    >
      <div className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="del-title">
        <h2 className="dialog-title" id="del-title">
          Delete this message?
        </h2>
        <p className="dialog-text">
          It disappears for both of you, and there is no way to bring it back.
        </p>
        <span className="dialog-quote">{message.content}</span>
        <div className="dialog-actions">
          <button type="button" className="btn-text" ref={cancelRef} onClick={onCancel}>
            Keep it
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm}>
            Delete message
          </button>
        </div>
      </div>
    </div>
  )
}
