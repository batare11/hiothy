const { request } = require("../../utils/request");
const { formatDateTime } = require("../../utils/date");

Page({
  data: {
    tabs: [
      { label: "最新消息", value: "unread" },
      { label: "已读消息", value: "read" }
    ],
    activeTab: "unread",
    activeTabIndex: 0,
    messages: [],
    unreadCount: 0,
    loading: false
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar();
    if (tabBar) tabBar.setData({ selected: 2 });
    this.setData({
      activeTab: "unread",
      activeTabIndex: 0
    }, () => {
      Promise.all([
        this.loadMessages(),
        this.loadUnreadCount()
      ]);
    });
  },

  onPullDownRefresh() {
    Promise.all([this.loadMessages(), this.loadUnreadCount()])
      .finally(() => wx.stopPullDownRefresh());
  },

  changeTab(event) {
    const activeTab = event.currentTarget.dataset.value;
    const activeTabIndex = Number(event.currentTarget.dataset.index);
    this.setData({ activeTab, activeTabIndex }, () => {
      this.loadMessages();
    });
  },

  async loadMessages() {
    const requestedTab = this.data.activeTab;
    this.setData({ loading: true });
    try {
      const response = await request({
        url: "/messages",
        data: { state: requestedTab },
        silent: true
      });
      if (requestedTab !== this.data.activeTab) return;
      const messages = (response.data || []).map((item) => ({
        ...item,
        displayTime: formatDateTime(item.created_at),
        severityText: {
          info: "通知",
          warning: "关注",
          high: "较高风险",
          critical: "紧急关注"
        }[item.severity] || "通知"
      }));
      this.setData({ messages });
    } catch (error) {
      if (requestedTab === this.data.activeTab) {
        this.setData({ messages: [] });
      }
    } finally {
      if (requestedTab === this.data.activeTab) {
        this.setData({ loading: false });
      }
    }
  },

  async loadUnreadCount() {
    try {
      const response = await request({
        url: "/messages/unread-count",
        silent: true
      });
      this.setData({
        unreadCount: response.data && response.data.count
          ? response.data.count
          : 0
      });
      const tabBar = this.getTabBar && this.getTabBar();
      if (tabBar && tabBar.setUnreadCount) {
        tabBar.setUnreadCount(this.data.unreadCount);
      }
    } catch (error) {
      this.setData({ unreadCount: 0 });
      const tabBar = this.getTabBar && this.getTabBar();
      if (tabBar && tabBar.setUnreadCount) tabBar.setUnreadCount(0);
    }
  },

  openMessage(event) {
    const id = Number(event.currentTarget.dataset.id);
    const message = this.data.messages.find((item) => item.id === id);
    if (!message) return;
    const canOpenAnalysis = message.action_path === "/pages/analysis/index";
    wx.showModal({
      title: message.title,
      content: message.content,
      showCancel: canOpenAnalysis,
      cancelText: "关闭",
      confirmText: canOpenAnalysis ? "查看分析" : "我知道了",
      success: async ({ confirm, cancel }) => {
        if ((confirm || cancel) && !message.is_read) {
          await this.markAsRead(id, false);
        }
        if (confirm && canOpenAnalysis) {
          wx.switchTab({ url: message.action_path });
        }
      }
    });
  },

  async markAsRead(id, refresh = true) {
    try {
      await request({
        url: `/messages/${id}/read`,
        method: "PUT",
        silent: true
      });
      if (refresh) {
        this.loadMessages();
        this.loadUnreadCount();
      } else {
        await Promise.all([this.loadMessages(), this.loadUnreadCount()]);
      }
    } catch (error) {
      wx.showToast({ title: "标记已读失败", icon: "none" });
    }
  }
});
