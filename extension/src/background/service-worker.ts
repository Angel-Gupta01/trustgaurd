// extension/src/background/service-worker.ts

console.log("[TrustGuard] Service Worker initialized.");

// Create context menu items on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "trustguard-scan-selection",
    title: "Scan selection with TrustGuard",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "trustguard-verify-image",
    title: "Verify media provenance with TrustGuard",
    contexts: ["image", "video"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "trustguard-scan-selection" && info.selectionText) {
    chrome.action.openPopup?.();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PAGE_SCAN_ALERT") {
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#EF4444" });
  }
  sendResponse({ status: "acknowledged" });
});
