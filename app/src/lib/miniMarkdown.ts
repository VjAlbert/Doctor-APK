/**
 * Just enough Markdown for an AI answer: paragraphs, "- " bullets and **bold**.
 * It produces plain data that React renders as elements, so model output can
 * never inject HTML into the page.
 */
export interface Inline {
  text: string
  bold: boolean
}

export type Block = { type: 'p'; inline: Inline[] } | { type: 'ul'; items: Inline[][] }

export function parseInline(line: string): Inline[] {
  return line
    .split(/\*\*(.+?)\*\*/g)
    .map((text, i) => ({ text, bold: i % 2 === 1 }))
    .filter((part) => part.text !== '')
}

export function parseBlocks(source: string): Block[] {
  const blocks: Block[] = []
  for (const raw of source.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const bullet = /^[-*•]\s+(.*)$/.exec(line)
    if (bullet) {
      const last = blocks[blocks.length - 1]
      const item = parseInline(bullet[1])
      if (last?.type === 'ul') last.items.push(item)
      else blocks.push({ type: 'ul', items: [item] })
    } else {
      blocks.push({ type: 'p', inline: parseInline(line.replace(/^#{1,6}\s+/, '')) })
    }
  }
  return blocks
}
