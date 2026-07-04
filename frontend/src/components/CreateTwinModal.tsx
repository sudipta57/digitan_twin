import { useState, useRef } from 'react'
import { apiClient } from '../api/client'
import type { DocType } from '../types'

type QueueKind = 'pdf' | 'whatsapp' | 'txt' | 'url' | 'text'
type QueueStatus = 'pending' | 'uploading' | 'done' | 'error'

// Matches lines like "12/25/2021, 10:34 AM - Grandpa Rajan: message" — used to tell a real
// WhatsApp .txt export apart from a plain-text file, since forcing every .txt through the
// WhatsApp line parser silently strips 100% of non-matching content (see the "empty chunk" bug).
const WHATSAPP_LINE_RE = /^\d{1,2}\/\d{1,2}\/\d{2,4},\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\s+-\s+.+?:\s+.+$/im

interface QueueItem {
  id: string
  kind: QueueKind
  file?: File
  url?: string
  text?: string
  title: string
  year: number
  docType: DocType
  senderName?: string
  status: QueueStatus
  error?: string
}

interface Props {
  onClose: () => void
  onCreated: (figureId: string, name: string) => void
}

const CURRENT_YEAR = new Date().getFullYear()
const DOC_TYPE_OPTIONS: DocType[] = ['book', 'letter', 'diary', 'article', 'interview', 'paper', 'testimony', 'lecture']

let uid = 0
const nextId = () => `q${uid++}`

export function CreateTwinModal({ onClose, onCreated }: Props) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [yearsFrom, setYearsFrom] = useState('')
  const [yearsTo, setYearsTo] = useState('')
  const [relationship, setRelationship] = useState('')
  const [bio, setBio] = useState('')

  const [figureId, setFigureId] = useState<string | null>(null)
  const [queue, setQueue] = useState<QueueItem[]>([])

  const [urlInput, setUrlInput] = useState('')
  const [textTitle, setTextTitle] = useState('')
  const [textYear, setTextYear] = useState(String(CURRENT_YEAR))
  const [textBody, setTextBody] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleCreateBasicInfo = async () => {
    if (!name.trim() || !yearsFrom.trim()) {
      setFormError('Name and start year are required.')
      return
    }
    setSubmitting(true)
    setFormError(null)
    try {
      const res = await apiClient.createFigure({
        name: name.trim(),
        years_from: parseInt(yearsFrom, 10),
        years_to: yearsTo.trim() ? parseInt(yearsTo, 10) : undefined,
        relationship: relationship.trim() || undefined,
        bio: bio.trim() || undefined,
      })
      setFigureId(res.figure_id)
      setStep(2)
    } catch (err) {
      console.error(err)
      setFormError('Could not create twin. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const addFiles = async (files: FileList | null) => {
    if (!files) return
    const items: QueueItem[] = []
    for (const file of Array.from(files)) {
      const isPdf = file.name.toLowerCase().endsWith('.pdf')
      let kind: QueueKind = isPdf ? 'pdf' : 'txt'
      if (!isPdf) {
        const sample = (await file.text()).slice(0, 3000)
        if (WHATSAPP_LINE_RE.test(sample)) kind = 'whatsapp'
      }
      items.push({
        id: nextId(),
        kind,
        file,
        title: file.name.replace(/\.(pdf|txt)$/i, ''),
        year: CURRENT_YEAR,
        docType: isPdf ? 'book' : kind === 'whatsapp' ? 'whatsapp' : 'diary',
        senderName: kind === 'whatsapp' ? name : undefined,
        status: 'pending',
      })
    }
    setQueue(prev => [...prev, ...items])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const addUrl = () => {
    if (!urlInput.trim()) return
    setQueue(prev => [...prev, {
      id: nextId(), kind: 'url', url: urlInput.trim(),
      title: urlInput.trim(), year: CURRENT_YEAR, docType: 'article', status: 'pending',
    }])
    setUrlInput('')
  }

  const addText = () => {
    if (!textBody.trim() || !textTitle.trim()) return
    setQueue(prev => [...prev, {
      id: nextId(), kind: 'text', text: textBody.trim(),
      title: textTitle.trim(), year: parseInt(textYear, 10) || CURRENT_YEAR,
      docType: 'diary', status: 'pending',
    }])
    setTextTitle('')
    setTextBody('')
  }

  const updateItem = (id: string, patch: Partial<QueueItem>) => {
    setQueue(prev => prev.map(item => (item.id === id ? { ...item, ...patch } : item)))
  }

  const removeItem = (id: string) => {
    setQueue(prev => prev.filter(item => item.id !== id))
  }

  const runUploads = async () => {
    if (!figureId) return
    setStep(3)
    for (const item of queue) {
      updateItem(item.id, { status: 'uploading' })
      try {
        if (item.kind === 'pdf' && item.file) {
          await apiClient.ingestPdf(figureId, item.file, item.title, item.year)
        } else if (item.kind === 'whatsapp' && item.file) {
          await apiClient.ingestWhatsapp(figureId, item.file, item.senderName || name, item.year)
        } else if (item.kind === 'txt' && item.file) {
          const text = await item.file.text()
          await apiClient.ingestText(figureId, text, item.title, item.year, item.docType)
        } else if (item.kind === 'url' && item.url) {
          await apiClient.ingestUrl(figureId, item.url, item.title, item.year, item.docType)
        } else if (item.kind === 'text' && item.text) {
          await apiClient.ingestText(figureId, item.text, item.title, item.year, item.docType)
        }
        updateItem(item.id, { status: 'done' })
      } catch (err) {
        console.error(err)
        updateItem(item.id, { status: 'error', error: 'Upload failed' })
      }
    }
  }

  const finish = () => {
    if (figureId) onCreated(figureId, name)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-700 rounded-xl shadow-xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-semibold text-white">Create a Digital Twin</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 text-sm">✕</button>
        </div>

        <div className="overflow-y-auto px-5 py-4 flex-1">
          {step === 1 && (
            <div className="flex flex-col gap-3">
              <label className="text-xs text-zinc-400">
                Name
                <input value={name} onChange={e => setName(e.target.value)}
                  placeholder="Grandpa Rajan"
                  className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-amber-500" />
              </label>
              <div className="flex gap-3">
                <label className="text-xs text-zinc-400 flex-1">
                  Born
                  <input value={yearsFrom} onChange={e => setYearsFrom(e.target.value)}
                    placeholder="1940" inputMode="numeric"
                    className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-amber-500" />
                </label>
                <label className="text-xs text-zinc-400 flex-1">
                  Died (optional)
                  <input value={yearsTo} onChange={e => setYearsTo(e.target.value)}
                    placeholder="2021" inputMode="numeric"
                    className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-amber-500" />
                </label>
              </div>
              <label className="text-xs text-zinc-400">
                Relationship (optional)
                <input value={relationship} onChange={e => setRelationship(e.target.value)}
                  placeholder="Grandfather"
                  className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-amber-500" />
              </label>
              <label className="text-xs text-zinc-400">
                Short bio (optional)
                <textarea value={bio} onChange={e => setBio(e.target.value)}
                  placeholder="Engineer from Kolkata, wrote letters every week"
                  rows={2}
                  className="mt-1 w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-amber-500" />
              </label>
              {formError && <p className="text-xs text-red-400">{formError}</p>}
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-zinc-500">
                Add everything you have — WhatsApp exports, PDFs, letters, blog URLs, or pasted text.
                Each source is cited by name and year when {name || 'they'} responds.
              </p>

              <div className="border border-dashed border-zinc-700 rounded-lg p-4 text-center">
                <input ref={fileInputRef} type="file" multiple accept=".pdf,.txt"
                  onChange={e => addFiles(e.target.files)} className="hidden" id="twin-file-input" />
                <label htmlFor="twin-file-input" className="cursor-pointer text-xs text-amber-400 hover:text-amber-300">
                  Click to upload PDFs, WhatsApp .txt exports, or plain text files
                </label>
                <p className="text-[10px] text-zinc-600 mt-1">
                  .txt files are auto-detected as WhatsApp export or plain text — you can override below
                </p>
              </div>

              <div className="flex gap-2">
                <input value={urlInput} onChange={e => setUrlInput(e.target.value)}
                  placeholder="https://example.com/blog-post"
                  className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-amber-500" />
                <button onClick={addUrl} className="px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 hover:border-amber-500">
                  Add URL
                </button>
              </div>

              <div className="flex flex-col gap-2 border border-zinc-800 rounded-lg p-3">
                <input value={textTitle} onChange={e => setTextTitle(e.target.value)}
                  placeholder="Source title, e.g. Letter to Father 1987"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-amber-500" />
                <div className="flex gap-2">
                  <input value={textYear} onChange={e => setTextYear(e.target.value)}
                    placeholder="Year" inputMode="numeric"
                    className="w-24 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-amber-500" />
                  <textarea value={textBody} onChange={e => setTextBody(e.target.value)}
                    placeholder="Paste text..." rows={2}
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-amber-500" />
                </div>
                <button onClick={addText} className="self-end px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 hover:border-amber-500">
                  Add Text
                </button>
              </div>

              {queue.length > 0 && (
                <div className="flex flex-col gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
                    Queued sources ({queue.length})
                  </h3>
                  {queue.map(item => (
                    <div key={item.id} className="flex flex-col gap-1.5 bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">
                          {item.kind === 'pdf' ? '📄' : item.kind === 'whatsapp' ? '💬' : item.kind === 'url' ? '🔗' : '📝'}
                        </span>
                        <input value={item.title} onChange={e => updateItem(item.id, { title: e.target.value })}
                          className="flex-1 bg-transparent text-xs text-zinc-200 outline-none" />
                        <input value={item.year} onChange={e => updateItem(item.id, { year: parseInt(e.target.value, 10) || CURRENT_YEAR })}
                          className="w-16 bg-transparent text-xs text-zinc-400 outline-none" />
                        {item.kind === 'whatsapp' && (
                          <input value={item.senderName || ''} onChange={e => updateItem(item.id, { senderName: e.target.value })}
                            placeholder="name in chat"
                            className="w-28 bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300 outline-none" />
                        )}
                        {(item.kind === 'url' || item.kind === 'pdf' || item.kind === 'txt') && (
                          <select value={item.docType} onChange={e => updateItem(item.id, { docType: e.target.value as DocType })}
                            className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300 outline-none">
                            {DOC_TYPE_OPTIONS.map(dt => <option key={dt} value={dt}>{dt}</option>)}
                          </select>
                        )}
                        <button onClick={() => removeItem(item.id)} className="text-zinc-600 hover:text-red-400 text-xs">✕</button>
                      </div>
                      {(item.kind === 'whatsapp' || item.kind === 'txt') && (
                        <div className="flex items-center gap-2 pl-6">
                          <span className="text-[10px] text-zinc-600">This .txt file is:</span>
                          <div className="flex rounded-md overflow-hidden border border-zinc-700 text-[10px]">
                            <button type="button"
                              onClick={() => updateItem(item.id, { kind: 'whatsapp', docType: 'whatsapp', senderName: item.senderName || name })}
                              className={`px-2 py-0.5 ${item.kind === 'whatsapp' ? 'bg-amber-500 text-zinc-900' : 'bg-zinc-900 text-zinc-400'}`}>
                              WhatsApp export
                            </button>
                            <button type="button"
                              onClick={() => updateItem(item.id, { kind: 'txt', docType: 'diary' })}
                              className={`px-2 py-0.5 ${item.kind === 'txt' ? 'bg-amber-500 text-zinc-900' : 'bg-zinc-900 text-zinc-400'}`}>
                              Plain text
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-1">
                Building the memory graph
              </h3>
              {queue.map(item => (
                <div key={item.id} className="flex items-center justify-between px-3 py-2 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                  <span className="text-xs text-zinc-300 truncate">{item.title}</span>
                  <span className="text-xs">
                    {item.status === 'pending' && <span className="text-zinc-600">Waiting…</span>}
                    {item.status === 'uploading' && <span className="text-amber-400 animate-pulse">Processing…</span>}
                    {item.status === 'done' && <span className="text-emerald-400">✓ Done</span>}
                    {item.status === 'error' && <span className="text-red-400">Failed</span>}
                  </span>
                </div>
              ))}
              {queue.length === 0 && <p className="text-xs text-zinc-500">No sources queued.</p>}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800">
          {step === 1 && (
            <>
              <span />
              <button onClick={handleCreateBasicInfo} disabled={submitting}
                className="px-4 py-2 rounded-lg bg-amber-500 text-zinc-900 text-xs font-semibold hover:bg-amber-400 disabled:opacity-50">
                {submitting ? 'Creating…' : 'Next: Add Sources'}
              </button>
            </>
          )}
          {step === 2 && (
            <>
              <button onClick={finish} className="text-xs text-zinc-500 hover:text-zinc-300">
                Skip for now
              </button>
              <button onClick={runUploads} disabled={queue.length === 0}
                className="px-4 py-2 rounded-lg bg-amber-500 text-zinc-900 text-xs font-semibold hover:bg-amber-400 disabled:opacity-50">
                Upload {queue.length} source{queue.length === 1 ? '' : 's'}
              </button>
            </>
          )}
          {step === 3 && (
            <>
              <span />
              <button onClick={finish}
                disabled={queue.some(item => item.status === 'pending' || item.status === 'uploading')}
                className="px-4 py-2 rounded-lg bg-amber-500 text-zinc-900 text-xs font-semibold hover:bg-amber-400 disabled:opacity-50">
                Done — Start Talking
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
