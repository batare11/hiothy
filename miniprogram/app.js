const { BASE_URL, REQUEST_TIMEOUT } = require("./config/index");

function wechatLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      timeout: REQUEST_TIMEOUT,
      success: ({ code }) => {
        if (code) resolve(code);
        else reject(new Error("微信未返回登录凭证"));
      },
      fail: reject
    });
  });
}

function exchangeLoginCode(code) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}/auth/wechat-login`,
      method: "POST",
      data: { code },
      timeout: REQUEST_TIMEOUT,
      header: { "content-type": "application/json" },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data.data) {
          resolve(res.data.data);
          return;
        }
        const message = res.data && (res.data.detail || res.data.message);
        reject(new Error(message || `登录失败（${res.statusCode}）`));
      },
      fail: reject
    });
  });
}

App({
  globalData: {
    accessToken: "",
    miniUserId: "",
    userProfile: null,
    accessInfo: null,
    loginPromise: null
  },

  onLaunch() {
    this.globalData.accessToken = wx.getStorageSync("accessToken") || "";
    this.globalData.miniUserId = wx.getStorageSync("wechatUserId") || "";
    this.ensureLogin().catch((error) => {
      console.error("微信登录失败", error);
    });
  },

  clearLogin() {
    this.globalData.accessToken = "";
    this.globalData.miniUserId = "";
    this.globalData.accessInfo = null;
    wx.removeStorageSync("accessToken");
    wx.removeStorageSync("accessTokenExpiresAt");
    wx.removeStorageSync("wechatUserId");
  },

  async refreshAccess() {
    const { request } = require("./utils/request");
    const response = await request({
      url: "/access/me",
      silent: true
    });
    this.globalData.accessInfo = response.data || {
      role: "free",
      role_name: "免费用户",
      permissions: [],
      is_admin: false
    };
    return this.globalData.accessInfo;
  },

  hasPermission(permission) {
    const access = this.globalData.accessInfo || {};
    return (access.permissions || []).includes(permission);
  },

  async ensureLogin(force = false) {
    const expiresAt = Number(wx.getStorageSync("accessTokenExpiresAt") || 0);
    const tokenValid = (
      this.globalData.accessToken &&
      expiresAt > Date.now() + 60 * 1000
    );
    if (!force && tokenValid) return this.globalData.accessToken;
    if (this.globalData.loginPromise) return this.globalData.loginPromise;

    if (force) this.clearLogin();
    this.globalData.loginPromise = (async () => {
      const code = await wechatLogin();
      const result = await exchangeLoginCode(code);
      const expiresAtValue = Date.now() + Number(result.expires_in) * 1000;

      this.globalData.accessToken = result.access_token;
      this.globalData.miniUserId = result.user_id;
      wx.setStorageSync("accessToken", result.access_token);
      wx.setStorageSync("accessTokenExpiresAt", expiresAtValue);
      wx.setStorageSync("wechatUserId", result.user_id);
      return result.access_token;
    })();

    try {
      return await this.globalData.loginPromise;
    } finally {
      this.globalData.loginPromise = null;
    }
  }
});
