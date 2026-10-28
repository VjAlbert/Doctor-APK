/** Incremental parser for line-delimited JSON arriving in arbitrary byte chunks. */
export function createNdjsonParser(onValue: (value: unknown) => void) {
  const decoder = new TextDecoder()
  let buffer = ''

  const flushLine = (line: string) => {
    const trimmed = line.trim()
    if (trimmed) onValue(JSON.parse(trimmed))
  }

  return {
    push(chunk: Uint8Array) {
      buffer += decoder.decode(chunk, { stream: true })
      let newline = buffer.indexOf('\n')
      while (newline >= 0) {
        flushLine(buffer.slice(0, newline))
        buffer = buffer.slice(newline + 1)
        newline = buffer.indexOf('\n')
      }
    },
    end() {
      buffer += decoder.decode()
      const rest = buffer
      buffer = ''
      flushLine(rest)
    },
  }
}
