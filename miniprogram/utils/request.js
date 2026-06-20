const {
  BASE_URL,
  REQUEST_TIMEOUT,
  UPLOAD_TIMEOUT
} = require("../config/index");

function getUserId() {
  const app = getApp();
  return app.globalData.miniUserId || wx.getStorageSync("miniUserId") || "demo-user";
}

function showError(message) {
  wx.showToast({
    title: message || "请求失败，请稍后重试",
    icon: "none",
    duration: 2500
  });
}

function getNetworkErrorMessage(error, action = "请求") {
  const detail = error && error.errMsg ? error.errMsg : "";
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

function request(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || "GET",
      data: options.data || {},
      timeout: REQUEST_TIMEOUT,
      header: {
        "content-type": "application/json",
        "X-Mini-User-Id": getUserId(),
        ...(options.header || {})
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        const message = res.data && (res.data.detail || res.data.message);
        if (!options.silent) showError(message);
        reject(new Error(message || `请求失败（${res.statusCode}）`));
      },
      fail(error) {
        if (!options.silent) {
          showError(getNetworkErrorMessage(error));
        }
        reject(error);
      }
    });
  });
}

function checkBackend() {
  return request({
    url: "/health",
    silent: true
  }).catch((error) => {
    const message = getNetworkErrorMessage(error, "连接后端");
    showError(message);
    throw new Error(message);
  });
}

async function uploadImage(filePath) {
  // 先验证基础连接，避免把“后端未启动”误报成“图片上传失败”。
  await checkBackend();

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/ocr/blood-pressure`,
      filePath,
      name: "file",
      timeout: UPLOAD_TIMEOUT,
      header: {
        "X-Mini-User-Id": getUserId()
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
