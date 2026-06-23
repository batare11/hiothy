const { request } = require("../utils/request");

const BASE_TABS = [
  { pagePath: "/pages/home/index", text: "首页", icon: "home" },
  { pagePath: "/pages/analysis/index", text: "分析", icon: "chart" },
  { pagePath: "/pages/messages/index", text: "消息", icon: "message" },
  { pagePath: "/pages/profile/index", text: "我的", icon: "profile" }
];

Component({
  data: {
    selected: 0,
    unreadCount: 0,
    unreadBadge: "",
    tabs: BASE_TABS
  },

  lifetimes: {
    attached() {
      this.refreshUnreadCount();
      this.refreshAccessTabs();
    }
  },

  methods: {
    async refreshAccessTabs() {
      try {
        const access = await getApp().refreshAccess();
        const tabs = access.is_admin
          ? [
              ...BASE_TABS,
              { pagePath: "/pages/admin/index", text: "管理", icon: "admin" }
            ]
          : BASE_TABS;
        this.setData({ tabs });
      } catch (error) {
        this.setData({ tabs: BASE_TABS });
      }
    },
    setUnreadCount(count) {
      const unreadCount = Math.max(0, Number(count) || 0);
      this.setData({
        unreadCount,
        unreadBadge: unreadCount > 99 ? "99+" : String(unreadCount)
      });
    },

    async refreshUnreadCount() {
      try {
        const response = await request({
          url: "/messages/unread-count",
          silent: true
        });
        const count = response.data && response.data.count
          ? response.data.count
          : 0;
        this.setUnreadCount(count);
      } catch (error) {
        this.setUnreadCount(0);
      }
    },

    switchTab(event) {
      const index = Number(event.currentTarget.dataset.index);
      const tab = this.data.tabs[index];
      if (!tab || index === this.data.selected) return;
      wx.switchTab({ url: tab.pagePath });
    }
  }
});
