import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

// Shared a11y behavior for the app's hand-rolled `.modal-overlay`/`.modal-card`
// dialogs: focuses the dialog on open, restores focus to the trigger on
// close, and traps Tab/Shift+Tab within the dialog so keyboard users can't
// tab into content hidden behind the overlay. Attach the returned ref to the
// `.modal-card` element (which needs `tabIndex={-1}` to be focusable as a
// fallback when it has no focusable children).
//
// `isOpen` matters for callers whose component stays mounted while the
// dialog itself is conditionally rendered (e.g. a confirm dialog owned by a
// toolbar button) - a ref's identity change isn't reactive, so without this
// the effect has no way to know when the dialog actually entered the DOM.
// A caller that only ever mounts this hook's owning component while the
// dialog is open (e.g. the dialog IS the component) can just pass `true`.
export function useModalFocusTrap(isOpen: boolean, onClose: () => void) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    const dialog = dialogRef.current
    const previouslyFocused = document.activeElement as HTMLElement | null

    function getFocusable(): HTMLElement[] {
      if (!dialog) return []
      return Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
    }

    const focusable = getFocusable()
    ;(focusable[0] ?? dialog)?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (event.key !== 'Tab') return
      const items = getFocusable()
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus()
    }
  }, [isOpen, onClose])

  return dialogRef
}
