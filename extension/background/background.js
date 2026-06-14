chrome.runtime.onInstalled.addListener(() => {
  // Side panel se abre desde el botón de panel lateral de Chrome (no sobreescribe el popup)
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: false })
    .catch(console.error);
});
