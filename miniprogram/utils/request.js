const { BASE_URL, REQUEST_TIMEOUT } = require("../config/index");

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
        if (!options.silent) showError("网络连接失败，请检查服务地址");
        reject(error);
      }
    });
  });
}

function uploadImage(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/ocr/blood-pressure`,
      filePath,
      name: "file",
      timeout: 30000,
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
        showError("图片上传失败，请检查网络");
        reject(error);
      }
    });
  });
}

module.exports = {
  request,
  uploadImage
};

