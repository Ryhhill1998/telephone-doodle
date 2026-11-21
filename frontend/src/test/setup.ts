import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Testing Library does not auto-clean when `globals` is on in some setups, so
// unmount between tests explicitly to keep them independent.
afterEach(() => {
  cleanup()
})
