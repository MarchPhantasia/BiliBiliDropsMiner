const NATIVE_HOST = 'com.mi0e.bilibili_drops_miner';
const COOKIE_NAMES = new Set([
  'SESSDATA',
  'bili_jct',
  'DedeUserID',
  'DedeUserID__ckMd5',
  'buvid3',
  'b_nut',
  'sid',
]);

function setBadge(text, color) {
  chrome.action.setBadgeText({text});
  chrome.action.setBadgeBackgroundColor({color});
  setTimeout(() => chrome.action.setBadgeText({text: ''}), 4000);
}

async function readBilibiliCookies() {
  const cookies = await chrome.cookies.getAll({domain: '.bilibili.com'});
  return cookies
    .filter((cookie) => COOKIE_NAMES.has(cookie.name) && cookie.value)
    .map(({name, value}) => ({name, value}));
}

function sendToNativeHost(cookies) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST,
      {type: 'save_bilibili_cookies', cookies},
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!response || !response.ok) {
          reject(new Error(response?.error || 'Native host did not accept the cookie'));
          return;
        }
        resolve(response);
      },
    );
  });
}

async function syncCookie() {
  try {
    const cookies = await readBilibiliCookies();
    if (!cookies.some((cookie) => cookie.name === 'SESSDATA')) {
      throw new Error('当前 Chrome Profile 尚未登录 Bilibili');
    }
    const response = await sendToNativeHost(cookies);
    setBadge('OK', '#16803c');
    return response;
  } catch (error) {
    setBadge('!', '#c93737');
    throw error;
  }
}

chrome.action.onClicked.addListener(() => {
  syncCookie().catch(() => {});
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'sync_cookie') return false;
  syncCookie()
    .then((response) => sendResponse(response))
    .catch((error) => sendResponse({ok: false, error: error.message}));
  return true;
});
