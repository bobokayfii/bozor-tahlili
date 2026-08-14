// Navbar tugmalari uchun kichik chiziqli (stroke) ikonalar — currentColor
// ishlatiladi, shu sabab tugma hover holatida rang o'zgarganda ikonka ham
// birga o'zgaradi (statik PNG bilan bu mumkin emas edi).

export function RefreshIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M13.5 8a5.5 5.5 0 1 1-1.6-3.89"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path d="M13.5 2.5v3.5H10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// Solishtirish rejimi checklist ("checkbox tanlash") bilan ishlaydi, shu
// sabab mavhum "vs" belgisi o'rniga aynan shuni ifodalovchi — belgilangan
// checkbox — ikonka tanlandi.
export function CompareIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="12" height="12" rx="3" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M5 8.2 7.1 10.3 11.2 5.8"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function DownloadIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 2v7.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path
        d="M4.8 7.3 8 10.5l3.2-3.2"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M2.5 12.5v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}
