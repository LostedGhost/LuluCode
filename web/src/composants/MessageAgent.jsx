import { useMemo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

export default function MessageAgent({ texte }) {
  const html = useMemo(
    () => DOMPurify.sanitize(marked.parse(texte || ''), {
      FORBID_TAGS: ['style', 'form', 'input', 'iframe'],
    }),
    [texte],
  )
  return (
    <div className="bloc agent">
      <span className="etiquette">LuluCode</span>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}
