const { request } = require("../../utils/request");
const { formatDate } = require("../../utils/date");

Page({
  data: {
    profile: {
      nickname: "",
      avatar_url: "",
      gender: "",
      phone: "",
      birth_date: ""
    },
    genderOptions: ["男", "女", "其他", "不便透露"],
    genderIndex: 0,
    feedback: {
      content: "",
      contact: ""
    },
    today: formatDate(new Date()),
    shortUserId: "",
    avatarLetter: "健",
    saving: false,
    submittingFeedback: false
  },

  onLoad() {
    getApp().ensureLogin().then(() => {
      const userId = getApp().globalData.miniUserId || wx.getStorageSync("wechatUserId");
      this.setData({ shortUserId: userId.slice(-12) });
    }).catch(() => {
      this.setData({ shortUserId: "登录失败" });
    });
  },

  onShow() {
    this.loadProfile();
  },

  onPullDownRefresh() {
    this.loadProfile().finally(() => wx.stopPullDownRefresh());
  },

  async loadProfile() {
    try {
      const response = await request({ url: "/profile", silent: true });
      const profile = response.data || {};
      const genderIndex = Math.max(this.data.genderOptions.indexOf(profile.gender), 0);
      this.setData({
        profile,
        genderIndex,
        avatarLetter: (profile.nickname || "健").slice(0, 1)
      });
    } catch (error) {
      wx.showToast({ title: "资料加载失败", icon: "none" });
    }
  },

  chooseAvatar(event) {
    const avatarUrl = event.detail.avatarUrl;
    this.setData({ "profile.avatar_url": avatarUrl });
    wx.showToast({ title: "头像将在保存后生效", icon: "none" });
  },

  handleProfileInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`profile.${field}`]: event.detail.value });
    if (field === "nickname" && event.detail.value) {
      this.setData({ avatarLetter: event.detail.value.slice(0, 1) });
    }
  },

  changeGender(event) {
    const genderIndex = Number(event.detail.value);
    this.setData({
      genderIndex,
      "profile.gender": this.data.genderOptions[genderIndex]
    });
  },

  changeBirthDate(event) {
    this.setData({ "profile.birth_date": event.detail.value });
  },

  async saveProfile() {
    if (this.data.saving) return;
    if (!this.data.profile.nickname.trim()) {
      wx.showToast({ title: "请输入昵称", icon: "none" });
      return;
    }
    this.setData({ saving: true });
    try {
      const response = await request({
        url: "/profile",
        method: "PUT",
        data: this.data.profile
      });
      getApp().globalData.userProfile = response.data;
      wx.showToast({ title: "保存成功", icon: "success" });
    } finally {
      this.setData({ saving: false });
    }
  },

  handleFeedbackInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`feedback.${field}`]: event.detail.value });
  },

  async submitFeedback() {
    const content = this.data.feedback.content.trim();
    if (content.length < 2) {
      wx.showToast({ title: "请填写至少 2 个字", icon: "none" });
      return;
    }
    if (this.data.submittingFeedback) return;
    this.setData({ submittingFeedback: true });
    try {
      const response = await request({
        url: "/feedback",
        method: "POST",
        data: {
          content,
          contact: this.data.feedback.contact.trim() || null
        }
      });
      wx.showToast({ title: response.message || "提交成功", icon: "success" });
      this.setData({ feedback: { content: "", contact: "" } });
    } finally {
      this.setData({ submittingFeedback: false });
    }
  }
});
