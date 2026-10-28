import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { Radar } from './Radar'

describe('radar sweep', () => {
  const html = renderToStaticMarkup(createElement(Radar, { progress: 3 }))

  it('rotates around the radar centre with an explicit pivot', () => {
    // A CSS transform on the group pivots around the centre of its own bounding box, which made the
    // sweep wobble. The SVG animation names the pivot (0,0 is the centre of the viewBox) instead.
    expect(html).toContain('<animateTransform')
    expect(html).toContain('from="0 0 0"')
    expect(html).toContain('to="360 0 0"')
    expect(html).not.toMatch(/transform-origin|style="[^"]*rotate/)
  })

  it('draws the sweep and the rings from the same centre', () => {
    expect(html).toContain('viewBox="-110 -110 220 220"')
    expect(html).toContain('d="M0 0H104"')
  })
})
