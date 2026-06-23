const { request } = require("../../utils/request");
const { formatDateTime } = require("../../utils/date");

Page({
  data: {
    loading: false,
    accessDenied: false,
    adminMode: "feedback",
    status: "",
    statusOptions: [
      { value: "", label: "全部" },
      { value: "pending", label: "待处理" },
      { value: "resolved", label: "已处理" }
    ],
    items: [],
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    replyingId: 0,
    roleUpdatingKey: "",
    rbacLoading: false,
    roles: [],
    assignableRoles: [],
    permissions: [],
    newRole: {
      code: "",
      name: "",
      description: "",
      rank: 0
    },
    newPermission: {
      code: "",
      name: "",
      description: "",
      module: "general"
    },
    hasLoaded: false
  },

  onLoad() {
    this.loadFeedback();
    this.loadRbac();
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar();
    if (tabBar) {
      tabBar.setData({ selected: 4 });
      if (tabBar.refreshAccessTabs) tabBar.refreshAccessTabs();
    }
    if (this.data.hasLoaded) {
      if (this.data.adminMode === "rbac") this.loadRbac();
      else this.loadFeedback();
    }
  },

  onPullDownRefresh() {
    const task = this.data.adminMode === "rbac"
      ? this.loadRbac()
      : this.loadFeedback();
    task.finally(() => wx.stopPullDownRefresh());
  },

  changeAdminMode(event) {
    const adminMode = event.currentTarget.dataset.mode;
    this.setData({ adminMode });
    if (adminMode === "rbac" && !this.data.roles.length) this.loadRbac();
  },

  changeStatus(event) {
    this.setData({
      status: event.currentTarget.dataset.value,
      page: 1
    }, () => this.loadFeedback());
  },

  async loadFeedback() {
    if (this.data.loading) return;
    this.setData({ loading: true, accessDenied: false });
    try {
      const response = await request({
        url: "/admin/feedback",
        data: {
          page: this.data.page,
          page_size: this.data.pageSize,
          ...(this.data.status ? { status: this.data.status } : {})
        },
        silent: true
      });
      const data = response.data || {};
      this.setData({
        items: (data.items || []).map((item) => ({
          ...item,
          displayTime: formatDateTime(item.created_at),
          statusText: item.status === "resolved" ? "已处理" : "待处理"
        })),
        total: data.total || 0,
        totalPages: data.total_pages || 1,
        hasLoaded: true
      });
    } catch (error) {
      if (error.statusCode === 403) {
        this.setData({ accessDenied: true, items: [], hasLoaded: true });
      } else {
        wx.showToast({ title: error.message || "反馈加载失败", icon: "none" });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  normalizeRbac(data) {
    const permissions = data.permissions || [];
    return {
      permissions,
      roles: (data.roles || []).map((role) => ({
        ...role,
        permissionItems: permissions.map((permission) => ({
          ...permission,
          bound: (role.permission_codes || []).includes(permission.code)
        }))
      })),
      assignableRoles: (data.roles || []).filter((role) => role.enabled)
    };
  },

  async loadRbac() {
    if (this.data.rbacLoading) return;
    this.setData({ rbacLoading: true, accessDenied: false });
    try {
      const response = await request({
        url: "/admin/rbac",
        silent: true
      });
      this.setData(this.normalizeRbac(response.data || {}));
    } catch (error) {
      if (error.statusCode === 403) {
        this.setData({ accessDenied: true });
      } else {
        wx.showToast({ title: error.message || "权限配置加载失败", icon: "none" });
      }
    } finally {
      this.setData({ rbacLoading: false });
    }
  },

  handleRbacInput(event) {
    const scope = event.currentTarget.dataset.scope;
    const field = event.currentTarget.dataset.field;
    const index = Number(event.currentTarget.dataset.index);
    const value = event.detail.value;
    if (scope === "newRole" || scope === "newPermission") {
      this.setData({ [`${scope}.${field}`]: value });
      return;
    }
    this.setData({ [`${scope}[${index}].${field}`]: value });
  },

  handleRbacEnabled(event) {
    const scope = event.currentTarget.dataset.scope;
    const index = Number(event.currentTarget.dataset.index);
    this.setData({ [`${scope}[${index}].enabled`]: event.detail.value });
  },

  async createRole() {
    const role = this.data.newRole;
    if (!role.code.trim() || !role.name.trim()) {
      wx.showToast({ title: "请填写角色编码和名称", icon: "none" });
      return;
    }
    await request({
      url: "/admin/roles",
      method: "POST",
      data: {
        ...role,
        code: role.code.trim(),
        name: role.name.trim(),
        description: role.description.trim() || null,
        rank: Number(role.rank) || 0,
        enabled: true
      }
    });
    this.setData({
      newRole: { code: "", name: "", description: "", rank: 0 }
    });
    wx.showToast({ title: "角色已创建", icon: "success" });
    await this.loadRbac();
  },

  async saveRole(event) {
    const index = Number(event.currentTarget.dataset.index);
    const role = this.data.roles[index];
    await request({
      url: `/admin/roles/${role.code}`,
      method: "PUT",
      data: {
        name: role.name.trim(),
        description: role.description ? role.description.trim() : null,
        rank: Number(role.rank) || 0,
        enabled: Boolean(role.enabled)
      }
    });
    wx.showToast({ title: "角色已保存", icon: "success" });
    await this.loadRbac();
  },

  async createPermission() {
    const permission = this.data.newPermission;
    if (!permission.code.trim() || !permission.name.trim()) {
      wx.showToast({ title: "请填写权限编码和名称", icon: "none" });
      return;
    }
    await request({
      url: "/admin/permissions",
      method: "POST",
      data: {
        ...permission,
        code: permission.code.trim(),
        name: permission.name.trim(),
        description: permission.description.trim() || null,
        module: permission.module.trim() || "general",
        enabled: true
      }
    });
    this.setData({
      newPermission: {
        code: "",
        name: "",
        description: "",
        module: "general"
      }
    });
    wx.showToast({ title: "功能权限已创建", icon: "success" });
    await this.loadRbac();
  },

  async savePermission(event) {
    const index = Number(event.currentTarget.dataset.index);
    const permission = this.data.permissions[index];
    await request({
      url: `/admin/permissions/${permission.code}`,
      method: "PUT",
      data: {
        name: permission.name.trim(),
        description: permission.description
          ? permission.description.trim()
          : null,
        module: permission.module.trim() || "general",
        enabled: Boolean(permission.enabled)
      }
    });
    wx.showToast({ title: "功能权限已保存", icon: "success" });
    await this.loadRbac();
  },

  async toggleRolePermission(event) {
    const roleCode = event.currentTarget.dataset.role;
    const permissionCode = event.currentTarget.dataset.permission;
    const bound = event.currentTarget.dataset.bound === true ||
      event.currentTarget.dataset.bound === "true";
    await request({
      url: `/admin/roles/${roleCode}/permissions/${permissionCode}`,
      method: bound ? "DELETE" : "PUT"
    });
    wx.showToast({
      title: bound ? "已解绑" : "已绑定",
      icon: "success"
    });
    await this.loadRbac();
  },

  replyFeedback(event) {
    const id = Number(event.currentTarget.dataset.id);
    const item = this.data.items.find((entry) => entry.id === id);
    wx.showModal({
      title: "回复用户反馈",
      editable: true,
      placeholderText: "请输入回复内容",
      content: item && item.reply ? item.reply : "",
      confirmText: "发送回复",
      success: async ({ confirm, content }) => {
        if (!confirm) return;
        const reply = String(content || "").trim();
        if (reply.length < 2) {
          wx.showToast({ title: "回复至少填写 2 个字", icon: "none" });
          return;
        }
        this.setData({ replyingId: id });
        try {
          await request({
            url: `/admin/feedback/${id}/reply`,
            method: "PUT",
            data: { reply }
          });
          wx.showToast({ title: "回复成功", icon: "success" });
          await this.loadFeedback();
        } finally {
          this.setData({ replyingId: 0 });
        }
      }
    });
  },

  updateRole(event) {
    const userId = event.currentTarget.dataset.userId;
    const role = event.currentTarget.dataset.role;
    const roleNames = {
      vip: "VIP 普通会员",
      svip: "SVIP 超级会员",
      admin: "管理员"
    };
    const configuredRole = this.data.roles.find((item) => item.code === role);
    const roleName = configuredRole
      ? configuredRole.name
      : (roleNames[role] || role);
    wx.showModal({
      title: `授予${roleName}`,
      content: `确认给档案 ID ${userId} 授予${roleName}角色？`,
      confirmText: "确认授予",
      success: async ({ confirm }) => {
        if (!confirm) return;
        const key = `${userId}:${role}`;
        this.setData({ roleUpdatingKey: key });
        try {
          await request({
            url: `/admin/users/${userId}/role`,
            method: "PUT",
            data: { role }
          });
          wx.showToast({ title: "会员已开通", icon: "success" });
        } finally {
          this.setData({ roleUpdatingKey: "" });
        }
      }
    });
  },

  previousPage() {
    if (this.data.page <= 1) return;
    this.setData({ page: this.data.page - 1 }, () => this.loadFeedback());
  },

  nextPage() {
    if (this.data.page >= this.data.totalPages) return;
    this.setData({ page: this.data.page + 1 }, () => this.loadFeedback());
  }
});
