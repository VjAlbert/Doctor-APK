export interface Group {
  text: string
  same: boolean
}

/** Splits a hex fingerprint into groups of `size` characters, e.g. for display. */
export function groupHex(hex: string, size = 8): string[] {
  const groups: string[] = []
  for (let i = 0; i < hex.length; i += size) groups.push(hex.slice(i, i + size))
  return groups
}

/** Compares `found` against `expected` group by group, marking which groups match. */
export function diffFingerprint(found: string, expected: string, size = 8): Group[] {
  const want = groupHex(expected.toLowerCase(), size)
  return groupHex(found.toLowerCase(), size).map((text, i) => ({ text, same: text === want[i] }))
}

/** Index of the expected fingerprint closest to `found`, to compare like with like. */
export function closestExpected(found: string, expected: string[]): number {
  let best = 0
  let bestScore = -1
  expected.forEach((candidate, index) => {
    const score = diffFingerprint(found, candidate).filter((g) => g.same).length
    if (score > bestScore) {
      best = index
      bestScore = score
    }
  })
  return best
}
