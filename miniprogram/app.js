App({
  globalData: {
    miniUserId: "",
    userProfile: null
  },

  onLaunch() {
    let miniUserId = wx.getStorageSync("miniUserId");
    if (!miniUserId) {
      miniUserId = `dev-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
      wx.setStorageSync("miniUserId", miniUserId);
    }
    this.globalData.miniUserId = miniUserId;
  }
});

