const statusElement = document.getElementById('status');
const retryButton = document.getElementById('retry');

function runSync() {
  statusElement.textContent = '正在读取当前 Chrome Profile...';
  retryButton.hidden = true;
  chrome.runtime.sendMessage({type: 'sync_cookie'}, (response) => {
    if (chrome.runtime.lastError) {
      statusElement.textContent = chrome.runtime.lastError.message;
      retryButton.hidden = false;
      return;
    }
    if (!response?.ok) {
      statusElement.textContent = response?.error || 'Cookie 同步失败';
      retryButton.hidden = false;
      return;
    }
    statusElement.textContent = `已同步 ${response.saved_count} 项登录 Cookie，可以返回应用。`;
  });
}

retryButton.addEventListener('click', runSync);
runSync();
