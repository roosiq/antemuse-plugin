// Placeholder package for the desktop SDK's constants, so the harness can load
// desktop/plugin.js outside the app. The real '@hermes/plugin-sdk' is an app
// internal alias; `plugin.js` imports only these names from it.
export const PANES_AREA = 'panes'
export const TITLEBAR_AREAS = { center: 'titleBar.center', left: 'titleBar.left', right: 'titleBar.right' }
export const STATUSBAR_AREAS = { left: 'statusBar.left', right: 'statusBar.right' }
export const PALETTE_AREA = 'palette'
export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar.nav'
export const SETTINGS_PLUGINS_AREA = 'settings.plugins'
export const pluginSettingsHref = (id) => `/settings/plugins/${id}`

// The host state atoms the layer reads: focused conversation id, and whether the
// focused chat is working. `readonlyAtom` in the real SDK is a nanostores atom
// with get() and listen(); this mirrors that shape without the dependency.
export function atom(initial) {
  let value = initial
  const listeners = new Set()
  return {
    get: () => value,
    listen: (fn) => { listeners.add(fn); return () => listeners.delete(fn) },
    set: (next) => { value = next; for (const fn of listeners) fn(value) }
  }
}

export const host = {
  state: {
    activeSessionId: atom(null),
    focusedSessionId: atom(null),
    busy: atom(false)
  }
}
