const {
  BASE_URL,
  REQUEST_TIMEOUT,
  UPLOAD_TIMEOUT
} = require("../config/index");

function getAccessToken() {
  const app = getApp();
  return app.globalData.accessToken || wx.getStorageSync("accessToken") || "";
}

function showError(message) {
  wx.showToast({
    title: message || "请求失败，请稍后重试",
    icon: "none",
    duration: 2500
  });
}

function getNetworkErrorMessage(error, action = "请求") {
  const detail = error && (error.errMsg || error.message)
    ? (error.errMsg || error.message)
    : "";
  const lowerDetail = detail.toLowerCase();

  if (lowerDetail.includes("timeout")) {
    return `${action}超时，请稍后重试`;
  }
  if (
    lowerDetail.includes("url not in domain list") ||
    lowerDetail.includes("domain")
  ) {
    return "本地调试域名未放行，请在开发者工具中关闭合法域名校验";
  }
  if (
    lowerDetail.includes("connection refused") ||
    lowerDetail.includes("fail connect") ||
    lowerDetail.includes("unable to connect")
  ) {
    return "无法连接后端，请确认 Python 服务已在 5000 端口启动";
  }
  return `${action}失败：${detail || "请检查后端服务和网络配置"}`;
}

function sendRequest(options, token) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || "GET",
      data: options.data || {},
      timeout: REQUEST_TIMEOUT,
      header: {
        "content-type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.header || {})
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        const message = res.data && (res.data.detail || res.data.message);
        const error = new Error(message || `请求失败（${res.statusCode}）`);
        error.statusCode = res.statusCode;
        reject(error);
      },
      fail(error) {
        reject(new Error(getNetworkErrorMessage(error)));
      }
    });
  });
}

async function request(options) {
  const needsAuth = options.auth !== false;
  let token = "";
  if (needsAuth) token = await getApp().ensureLogin();

  try {
    return await sendRequest(options, token);
  } catch (error) {
    if (needsAuth && error.statusCode === 401 && !options._retried) {
      await getApp().ensureLogin(true);
      return request({ ...options, _retried: true });
    }
    if (!options.silent) showError(error.message);
    throw error;
  }
}

function checkBackend() {
  return request({
    url: "/health",
    auth: false,
    silent: true
  }).catch((error) => {
    const message = error.message || getNetworkErrorMessage(error, "连接后端");
    showError(message);
    throw new Error(message);
  });
}

async function uploadImage(filePath, engine = "rapid") {
  // 先验证基础连接，避免把“后端未启动”误报成“图片上传失败”。
  await checkBackend();

  await getApp().ensureLogin();
  return uploadImageOnce(filePath, engine, false);
}

function uploadImageOnce(filePath, engine, retried) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/ocr/blood-pressure?engine=${encodeURIComponent(engine)}`,
      filePath,
      name: "file",
      timeout: UPLOAD_TIMEOUT,
      header: {
        Authorization: `Bearer ${getAccessToken()}`
      },
      success(res) {
        let body = {};
        try {
          body = JSON.parse(res.data);
        } catch (error) {
          reject(new Error("服务器返回格式异常"));
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(body);
          return;
        }
        if (res.statusCode === 401 && !retried) {
          getApp().ensureLogin(true)
            .then(() => uploadImageOnce(filePath, engine, true))
            .then(resolve)
            .catch(reject);
          return;
        }
        const message = body.detail || body.message || "图片识别失败";
        showError(message);
        reject(new Error(message));
      },
      fail(error) {
        const message = getNetworkErrorMessage(error, "图片上传");
        showError(message);
        console.error("wx.uploadFile failed", {
          url: `${BASE_URL}/ocr/blood-pressure`,
          filePath,
          error
        });
        reject(new Error(message));
      }
    });
  });
}

module.exports = {
  request,
  uploadImage
};
