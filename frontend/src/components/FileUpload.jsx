import { useRef, useState } from 'react'
import { UploadCloud, FileText, X, Lightbulb, ChevronDown } from 'lucide-react'

const ACCEPT = '.csv,.xlsx,.json'
const MAX_BYTES = 50 * 1024 * 1024

function fmtSize(b) {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

export default function FileUpload({ onUpload, disabled = false }) {
  const inputRef = useRef(null)
  const [drag, setDrag] = useState(false)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [tipsOpen, setTipsOpen] = useState(true)

  const pick = (f) => {
    setError('')
    if (!f) return
    if (f.size > MAX_BYTES) {
      setError('File exceeds the 50 MB limit.')
      return
    }
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['csv', 'xlsx', 'json'].includes(ext)) {
      setError('Unsupported format. Use CSV, XLSX, or JSON.')
      return
    }
    setFile(f)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    if (disabled) return
    pick(e.dataTransfer.files?.[0])
  }

  const submit = async () => {
    if (!file || !onUpload) return
    setBusy(true)
    setError('')
    try {
      await onUpload(file)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } catch (err) {
      setError(err?.message || 'Upload failed.')
    } finally {
      setBusy(false)
    }
  }

  const clear = () => {
    setFile(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="space-y-3">
      <label
        onDragOver={(e) => {
          e.preventDefault()
          if (!disabled) setDrag(true)
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={`relative block cursor-pointer transition-colors rounded-[4px] px-5 py-7 border border-dashed ${
          drag ? 'border-accent-600 bg-accent-50' : 'border-rule-300 bg-paper-50'
        } ${disabled ? 'opacity-60' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          disabled={disabled}
          onChange={(e) => pick(e.target.files?.[0])}
        />
        <div className="flex flex-col items-center text-center gap-2">
          <span className="grid place-items-center h-11 w-11 rounded-[4px] bg-cream-50 text-ink-500">
            <UploadCloud size={20} />
          </span>
          <div>
            <div className="text-sm font-medium text-ink-900">
              Drop a file here, or <span className="text-accent-600 underline underline-offset-2">browse</span>
            </div>
            <div className="text-xs mt-1 text-ink-500">CSV, XLSX or JSON · up to 50 MB</div>
          </div>
        </div>
      </label>

      {error && (
        <div className="text-xs px-3 py-2 rounded-[4px] bg-rust-50 text-rust-700 border border-rule-300">
          {error}
        </div>
      )}

      <div className="rounded-[4px] overflow-hidden bg-cream-50 shadow-[inset_0_0_0_1px_var(--rule-300)]">
        <button
          type="button"
          onClick={() => setTipsOpen((v) => !v)}
          className="w-full flex items-center gap-2 px-3 py-2 text-left"
        >
          <Lightbulb size={14} className="text-accent-600 shrink-0" />
          <span className="text-xs font-medium flex-1 text-ink-900">
            Tip: name your file after the product or category for sharper insights
          </span>
          <ChevronDown
            size={14}
            className={`text-ink-500 transition-transform ${tipsOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {tipsOpen && (
          <div className="px-3 pb-3 text-xs space-y-2 text-ink-600 border-t border-rule-200 pt-2">
            <p>
              The model uses the file name to recognise the product or category and exclude it from aspects,
              keywords and topics — so the report focuses on what customers actually discuss.
            </p>
            <div>
              <div className="font-semibold mb-1 text-ink-900">Good names</div>
              <ul className="space-y-1 list-disc list-inside">
                <li>
                  <code className="ed-code">Airpods_Reviews.csv</code> — single product
                </li>
                <li>
                  <code className="ed-code">Amazon Echo 2 Reviews.csv</code> — brand + product
                </li>
                <li>
                  <code className="ed-code">Marriott_Hotel_Reviews.csv</code> — brand + category
                </li>
              </ul>
            </div>
            <div>
              <div className="font-semibold mb-1 text-ink-900">Avoid</div>
              <ul className="space-y-1 list-disc list-inside">
                <li>
                  <code className="ed-code">data.csv</code>, <code className="ed-code">reviews.csv</code> — no
                  signal
                </li>
              </ul>
            </div>
            <p className="opacity-90">
              Words like &ldquo;reviews&rdquo;, &ldquo;data&rdquo;, &ldquo;csv&rdquo; are ignored automatically.
            </p>
          </div>
        )}
      </div>

      {file && (
        <div className="rounded-[8px] bg-paper-100 shadow-[inset_0_0_0_1px_var(--rule-200)] p-3 flex items-center gap-3">
          <span className="grid place-items-center h-9 w-9 rounded-[4px] bg-cream-50 text-ink-500">
            <FileText size={16} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium truncate text-ink-900">{file.name}</div>
            <div className="text-xs text-ink-500">{fmtSize(file.size)}</div>
          </div>
          <button
            type="button"
            onClick={clear}
            aria-label="Remove file"
            className="btn-ghost !h-8 !w-8 !p-0"
            disabled={busy}
          >
            <X size={14} />
          </button>
          <button type="button" onClick={submit} disabled={disabled || busy} className="btn-primary !h-9">
            {busy ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      )}
    </div>
  )
}
