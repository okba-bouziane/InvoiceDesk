import { describe, expect, it } from 'vitest'
import fixture from './parity.json'
import { token2json } from './donut.ts'
import { checks, parseAmount, parseDate, tidy } from './normalize.ts'

// parity.json is written by scripts/parity_fixture.py from the Python code (the reference).
describe('the browser reader matches the Python code', () => {
  it('parses generated token sequences the same way', () => {
    for (const c of fixture.token2json) expect(token2json(c.in)).toEqual(c.out)
  })

  it('tidies real model output and runs the same checks', () => {
    for (const c of fixture.tidy_checks) {
      const t = tidy(c.in)
      expect(t).toEqual(c.tidy)
      expect(checks(t)).toEqual(c.checks)
    }
  })

  it('parses amounts and dates the same way', () => {
    for (const c of fixture.amounts) expect(parseAmount(c.in)).toEqual(c.out)
    for (const c of fixture.dates) expect(parseDate(c.in)).toEqual(c.out)
  })
})
