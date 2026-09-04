import test from 'node:test'
import assert from 'node:assert/strict'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

test('the same overhead file input remains available before and after image selection', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: UploadPanel } = await server.ssrLoadModule('/src/components/UploadPanel.jsx')
    for (const busy of [false, true]) {
      for (const file of [null, { name: 'overhead.png', size: 100, type: 'image/png' }]) {
        const html = renderToStaticMarkup(React.createElement(UploadPanel, { file, busy }))
        const inputs = html.match(/<input\b[^>]*aria-label="Select an overhead image"[^>]*>/g) || []
        assert.equal(inputs.length, 1)
        assert.match(inputs[0], /type="file"/)
        assert.doesNotMatch(inputs[0], /disabled/)
        assert.equal(html.includes('Replace Image'), Boolean(file))
      }
    }
  } finally {
    await server.close()
  }
})
