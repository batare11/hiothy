const { request } = require("../../utils/request");
const { formatDate, formatDateTime } = require("../../utils/date");

function formatBirthDate(value) {
  const matched = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  return matched ? `${matched[1]}年${matched[2]}月${matched[3]}日` : "";
}

Page({
  data: {
    profile: {
      nickname: "",
      avatar_url: "",
      gender: "",
      birth_date: ""
    },
    genderOptions: ["男", "女", "其他", "不便透露"],
    genderIndex: 0,
    feedback: {
      content: ""
    },
    feedbackHistory: [],
    feedbackTotal: 0,
    feedbackLoading: false,
    feedbackExpanded: false,
    today: formatDate(new Date()),
    birthDateText: "",
    shortUserId: "",
    avatarLetter: "健",
    saving: false,
    submittingFeedback: false,
    accessInfo: {
      role: "free",
      role_name: "免费用户",
      permissions: [],
      is_admin: false,
      available_roles: []
    },
    applyingRole: "",
    membershipExpanded: false,
    membershipBlessing: "",
    membershipFireworkLevel: "",
    membershipFireworks: [],
    deletingFeedbackId: 0,
    deletingMessageId: 0,
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
      this.loadFeedbackHistory(),
      this.loadAccess()
    ]);
    this.setData({ hasLoaded: true });
  },

  async loadProfile() {
    try {
      const response = await request({ url: "/profile", silent: true });
      const sourceProfile = response.data || {};
      const profile = {
        nickname: sourceProfile.nickname || "",
        avatar_url: sourceProfile.avatar_url || "",
        gender: sourceProfile.gender || "",
        birth_date: sourceProfile.birth_date || ""
      };
      const genderIndex = Math.max(this.data.genderOptions.indexOf(profile.gender), 0);
      this.setData({
        profile,
        birthDateText: formatBirthDate(profile.birth_date),
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

  handleAvatarError() {
    this.setData({ "profile.avatar_url": "" });
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
    this.setData({
      "profile.birth_date": event.detail.value,
      birthDateText: formatBirthDate(event.detail.value)
    });
  },

  async loadAccess() {
    try {
      const accessInfo = await getApp().refreshAccess();
      this.setData({ accessInfo });
      const tabBar = this.getTabBar && this.getTabBar();
      if (tabBar && tabBar.refreshAccessTabs) tabBar.refreshAccessTabs();
    } catch (error) {
      this.setData({
        accessInfo: {
          role: "free",
          role_name: "免费用户",
          permissions: [],
          is_admin: false,
          available_roles: []
        }
      });
    }
  },

  applyMembership(event) {
    const role = event.currentTarget.dataset.role;
    const configuredName = event.currentTarget.dataset.name;
    if (this.data.applyingRole) return;
    const roleName = configuredName || role;
    wx.showModal({
      title: `申请开通${roleName}`,
      content: "申请将发送给管理员，管理员处理后会通过反馈回复告知你。",
      confirmText: "提交申请",
      success: async ({ confirm }) => {
        if (!confirm) return;
        this.setData({ applyingRole: role });
        try {
          await request({
            url: "/feedback",
            method: "POST",
            data: {
              content: `【会员申请】申请开通${roleName}`
            }
          });
          wx.showToast({ title: "申请已提交", icon: "success" });
          await this.loadFeedbackHistory();
        } finally {
          this.setData({ applyingRole: "" });
        }
      }
    });
  },

  toggleMembershipService() {
    const access = this.data.accessInfo || {};
    const role = String(access.role || "").toLowerCase();
    const roleName = String(access.role_name || "").toLowerCase();
    const isSvip = role.includes("svip") || roleName.includes("svip") || roleName.includes("超级");
    const isVip = !isSvip && (
      role.includes("vip") || roleName.includes("vip") || roleName.includes("会员")
    );
    this.setData({
      membershipExpanded: !this.data.membershipExpanded
    });
    if (isSvip || isVip) {
      this.playMembershipFireworks(isSvip ? "svip" : "vip");
    }
  },

  playMembershipFireworks(level) {
    const count = level === "svip" ? 42 : 24;
    const palette = level === "svip"
      ? ["#FF4D8D", "#FFD166", "#7C5CFF", "#35D0FF", "#4ADE80", "#FF8A00"]
      : ["#FFD166", "#4DA3FF", "#52C41A", "#FF8A00"];
    const fireworks = Array.from({ length: count }).map((_, index) => ({
      id: `${Date.now()}-${index}`,
      left: 8 + Math.round(Math.random() * 84),
      top: 8 + Math.round(Math.random() * 46),
      size: level === "svip"
        ? 8 + Math.round(Math.random() * 8)
        : 6 + Math.round(Math.random() * 6),
      color: palette[index % palette.length],
      delay: Math.round(Math.random() * 360),
      duration: level === "svip"
        ? 900 + Math.round(Math.random() * 420)
        : 760 + Math.round(Math.random() * 280)
    }));
    this.setData({
      membershipBlessing: level === "svip"
        ? "尊贵的SVIP祝您身体健康！！"
        : "尊贵的VIP祝你身体健康！",
      membershipFireworkLevel: level,
      membershipFireworks: fireworks
    });
    if (this.membershipFireworkTimer) clearTimeout(this.membershipFireworkTimer);
    this.membershipFireworkTimer = setTimeout(() => {
      this.setData({
        membershipBlessing: "",
        membershipFireworkLevel: "",
        membershipFireworks: []
      });
    }, level === "svip" ? 1800 : 1400);
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
      const previousStateById = {};
      this.data.feedbackHistory.forEach((entry) => {
        previousStateById[entry.id] = {
          conversationExpanded: entry.conversationExpanded,
          replyDraft: entry.replyDraft,
          sendingMessage: entry.sendingMessage
        };
      });
      this.setData({
        feedbackHistory: (data.items || []).map((item) => {
          const previous = previousStateById[item.id] || {};
          return {
            ...item,
            displayTime: formatDateTime(item.created_at),
            messages: (item.messages || []).map((message) => ({
              ...message,
              displayTime: formatDateTime(message.created_at)
            })),
            conversationExpanded: Boolean(previous.conversationExpanded),
            replyDraft: previous.replyDraft || "",
            sendingMessage: Boolean(previous.sendingMessage),
            statusText: (statusMap[item.status] || statusMap.pending).text,
            statusStyle: (statusMap[item.status] || statusMap.pending).style
          };
        }),
        feedbackTotal: data.total || 0
      });
    } catch (error) {
      this.setData({ feedbackHistory: [], feedbackTotal: 0 });
    } finally {
      this.setData({ feedbackLoading: false });
    }
  },

  toggleFeedbackConversation(event) {
    const index = Number(event.currentTarget.dataset.index);
    const expanded = this.data.feedbackHistory[index].conversationExpanded;
    this.setData({
      [`feedbackHistory[${index}].conversationExpanded`]: !expanded
    });
  },

  handleConversationInput(event) {
    const index = Number(event.currentTarget.dataset.index);
    this.setData({
      [`feedbackHistory[${index}].replyDraft`]: event.detail.value
    });
  },

  async sendFeedbackMessage(event) {
    const index = Number(event.currentTarget.dataset.index);
    const item = this.data.feedbackHistory[index];
    const content = item.replyDraft.trim();
    if (content.length < 2 || item.sendingMessage) {
      if (content.length < 2) {
        wx.showToast({ title: "请填写至少 2 个字", icon: "none" });
      }
      return;
    }
    this.setData({ [`feedbackHistory[${index}].sendingMessage`]: true });
    try {
      await request({
        url: `/feedback/${item.id}/messages`,
        method: "POST",
        data: { content }
      });
      wx.showToast({ title: "消息已发送", icon: "success" });
      this.setData({
        [`feedbackHistory[${index}].replyDraft`]: ""
      });
      await this.loadFeedbackHistory();
    } finally {
      const current = this.data.feedbackHistory[index];
      if (current) {
        this.setData({
          [`feedbackHistory[${index}].sendingMessage`]: false
        });
      }
    }
  },

  deleteFeedback(event) {
    const id = Number(event.currentTarget.dataset.id);
    if (!id || this.data.deletingFeedbackId) return;
    wx.showModal({
      title: "删除反馈",
      content: "确定删除这条反馈？删除后该反馈和下方所有对话记录将不再展示，且不能恢复。",
      confirmText: "删除",
      confirmColor: "#E5484D",
      success: async ({ confirm }) => {
        if (!confirm) return;
        this.setData({ deletingFeedbackId: id });
        try {
          await request({
            url: `/feedback/${id}`,
            method: "DELETE"
          });
          wx.showToast({ title: "反馈已删除", icon: "success" });
          await this.loadFeedbackHistory();
        } finally {
          this.setData({ deletingFeedbackId: 0 });
        }
      }
    });
  },

  deleteFeedbackMessage(event) {
    const feedbackId = Number(event.currentTarget.dataset.feedbackId);
    const messageId = Number(event.currentTarget.dataset.messageId);
    if (!feedbackId || !messageId || this.data.deletingMessageId) return;
    wx.showModal({
      title: "撤回消息",
      content: "确定撤回这条消息？撤回后该消息将不再展示，且不能恢复。",
      confirmText: "撤回",
      confirmColor: "#E5484D",
      success: async ({ confirm }) => {
        if (!confirm) return;
        this.setData({ deletingMessageId: messageId });
        try {
          await request({
            url: `/feedback/${feedbackId}/messages/${messageId}`,
            method: "DELETE"
          });
          wx.showToast({ title: "消息已撤回", icon: "success" });
          await this.loadFeedbackHistory();
        } finally {
          this.setData({ deletingMessageId: 0 });
        }
      }
    });
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
          content
        }
      });
      wx.showToast({ title: response.message || "提交成功", icon: "success" });
      this.setData({ feedback: { content: "" } });
      await this.loadFeedbackHistory();
    } finally {
      this.setData({ submittingFeedback: false });
    }
  }
});
