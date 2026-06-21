const { request } = require("../../utils/request");
const { formatDate, formatDateTime } = require("../../utils/date");

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
    feedbackHistory: [],
    feedbackTotal: 0,
    feedbackLoading: false,
    feedbackExpanded: false,
    today: formatDate(new Date()),
    shortUserId: "",
    avatarLetter: "健",
    saving: false,
    submittingFeedback: false,
    hasLoaded: false
  },

  onLoad() {
    getApp().ensureLogin().then(() => {
      const userId = getApp().globalData.miniUserId || wx.getStorageSync("wechatUserId");
      this.setData({ shortUserId: userId.slice(-12) });
      return this.refreshPage();
    }).catch(() => {
      this.setData({ shortUserId: "登录失败" });
    });
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar();
    if (tabBar) {
      tabBar.setData({ selected: 3 });
      if (tabBar.refreshUnreadCount) tabBar.refreshUnreadCount();
    }
    if (this.data.hasLoaded) this.refreshPage();
  },

  onPullDownRefresh() {
    this.refreshPage()
      .finally(() => wx.stopPullDownRefresh());
  },

  async refreshPage() {
    await Promise.all([
      this.loadProfile(),
      this.loadFeedbackHistory()
    ]);
    this.setData({ hasLoaded: true });
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

  async loadFeedbackHistory() {
    if (this.data.feedbackLoading) return;
    this.setData({ feedbackLoading: true });
    try {
      const response = await request({
        url: "/feedback",
        data: {
          page: 1,
          page_size: this.data.feedbackExpanded ? 50 : 3
        },
        silent: true
      });
      const data = response.data || {};
      const statusMap = {
        pending: { text: "待处理", style: "pending" },
        processing: { text: "处理中", style: "processing" },
        resolved: { text: "已处理", style: "resolved" }
      };
      this.setData({
        feedbackHistory: (data.items || []).map((item) => ({
          ...item,
          displayTime: formatDateTime(item.created_at),
          statusText: (statusMap[item.status] || statusMap.pending).text,
          statusStyle: (statusMap[item.status] || statusMap.pending).style
        })),
        feedbackTotal: data.total || 0
      });
    } catch (error) {
      this.setData({ feedbackHistory: [], feedbackTotal: 0 });
    } finally {
      this.setData({ feedbackLoading: false });
    }
  },

  toggleFeedbackHistory() {
    this.setData({
      feedbackExpanded: !this.data.feedbackExpanded
    }, () => this.loadFeedbackHistory());
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
      await this.loadFeedbackHistory();
    } finally {
      this.setData({ submittingFeedback: false });
    }
  }
});
