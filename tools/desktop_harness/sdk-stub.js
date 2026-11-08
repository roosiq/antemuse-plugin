// Placeholder package for the desktop SDK's constants, so the harness can load
// desktop/plugin.js outside the app. The real '@hermes/plugin-sdk' is an app
// internal alias; `plugin.js` imports only these names from it.
export const PANES_AREA = 'panes'
export const STATUSBAR_AREAS = { left: 'statusBar.left', right: 'statusBar.right' }
export const PALETTE_AREA = 'palette'
export const SETTINGS_PLUGINS_AREA = 'settings.plugins'
export const pluginSettingsHref = (id) => `/settings/plugins/${id}`
