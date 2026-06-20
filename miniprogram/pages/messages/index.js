const { request } = require("../../utils/request");
const { formatDateTime } = require("../../utils/date");

Page({
  data: {
    tabs: [
      { label: "最新消息", value: "unread" },
      { label: "已读消息", value: "read" }
    ],
    activeTab: "unread",
    messages: [],
    unreadCount: 0,
    loading: false
  },

  onShow() {
    this.loadMessages();
    this.loadUnreadCount();
  },

  onPullDownRefresh() {
    Promise.all([this.loadMessages(), this.loadUnreadCount()])
      .finally(() => wx.stopPullDownRefresh());
  },

  changeTab(event) {
    this.setData({ activeTab: event.currentTarget.dataset.value }, () => {
      this.loadMessages();
    });
  },

  async loadMessages() {
    this.setData({ loading: true });
    try {
      const response = await request({
        url: "/messages",
        data: { state: this.data.activeTab },
        silent: true
      });
      const messages = (response.data || []).map((item) => ({
        ...item,
        displayTime: formatDateTime(item.created_at)
      }));
      this.setData({ messages });
    } catch (error) {
      this.setData({ messages: [] });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadUnreadCount() {
    try {
      const response = await request({
        url: "/messages",
        data: { state: "unread" },
        silent: true
      });
      this.setData({ unreadCount: (response.data || []).length });
    } catch (error) {
      this.setData({ unreadCount: 0 });
    }
  },

  openMessage(event) {
    const id = Number(event.currentTarget.dataset.id);
    const message = this.data.messages.find((item) => item.id === id);
    if (!message) return;
    wx.showModal({
      title: message.title,
      content: message.content,
      showCancel: false,
      confirmText: "我知道了",
      success: () => {
        if (!message.is_read) this.markAsRead(id);
      }
    });
  },

  async markAsRead(id) {
    try {
      await request({
        url: `/messages/${id}/read`,
        method: "PUT",
        silent: true
      });
      this.loadMessages();
      this.loadUnreadCount();
    } catch (error) {
      wx.showToast({ title: "标记已读失败", icon: "none" });
    }
  }
});

