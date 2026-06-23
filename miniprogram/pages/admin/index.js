const { request } = require("../../utils/request");
const { formatDateTime } = require("../../utils/date");

Page({
  data: {
    loading: false,
    accessDenied: false,
    adminMode: "feedback",
    status: "pending",
    statusOptions: [
      { value: "pending", label: "待处理" },
      { value: "resolved", label: "已处理" }
    ],
    items: [],
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    replyingId: 0,
    deletingFeedbackId: 0,
    revokingReplyId: 0,
    rbacLoading: false,
    roles: [],
    permissionAssignableRoles: [],
    assignableRoles: [],
    permissions: [],
    roleCreateVisible: false,
    permissionCreateVisible: false,
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
    userGrant: {
      archiveId: "",
      roleCode: "",
      roleName: ""
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
    this.setData({
      adminMode: "feedback",
      status: "pending",
      page: 1
    });
    if (this.data.hasLoaded) this.loadFeedback();
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
        items: (data.items || []).map((item) => {
          const messages = (item.messages || []).map((message) => ({
            ...message,
            displayTime: formatDateTime(message.created_at)
          }));
          const conversationMessages = messages.filter((message, index) => !(
            index === 0 &&
            message.sender_type === "user" &&
            message.content === item.content
          ));
          return {
            ...item,
            messages,
            conversationMessages,
            displayTime: formatDateTime(item.created_at),
            statusText: item.status === "resolved" ? "已处理" : "待处理"
          };
        }),
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
    const enabledPermissions = permissions.filter(
      (permission) => permission.enabled
    );
    const normalizedRoles = (data.roles || []).map((role) => ({
      ...role,
      expanded: false,
      permissionItems: enabledPermissions.map((permission) => ({
        ...permission,
        bound: (role.permission_codes || []).includes(permission.code)
      }))
    }));
    return {
      roles: normalizedRoles,
      permissionAssignableRoles: normalizedRoles.filter((role) => role.enabled),
      assignableRoles: (data.roles || []).filter((role) => role.enabled),
      permissions: permissions.map((permission) => ({
        ...permission,
        expanded: false
      }))
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
      const normalized = this.normalizeRbac(response.data || {});
      const selectedRoleStillEnabled = normalized.assignableRoles.some(
        (role) => role.code === this.data.userGrant.roleCode
      );
      this.setData({
        ...normalized,
        ...(!selectedRoleStillEnabled
          ? {
              userGrant: {
                ...this.data.userGrant,
                roleCode: "",
                roleName: ""
              }
            }
          : {})
      });
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
    if (
      scope === "newRole" ||
      scope === "newPermission" ||
      scope === "userGrant"
    ) {
      this.setData({ [`${scope}.${field}`]: value });
      return;
    }
    this.setData({ [`${scope}[${index}].${field}`]: value });
  },

  changeGrantRole(event) {
    const index = Number(event.detail.value);
    const role = this.data.assignableRoles[index];
    this.setData({
      "userGrant.roleCode": role ? role.code : "",
      "userGrant.roleName": role ? role.name : ""
    });
  },

  grantUserRole() {
    const archiveId = this.data.userGrant.archiveId.trim();
    const role = this.data.userGrant.roleCode;
    if (!archiveId || !role) {
      wx.showToast({ title: "请填写档案 ID 并选择角色", icon: "none" });
      return;
    }
    const selectedRole = this.data.assignableRoles.find(
      (item) => item.code === role
    );
    wx.showModal({
      title: "确认用户授权",
      content: `确认给档案 ID ${archiveId} 授予${selectedRole ? selectedRole.name : role}角色？`,
      confirmText: "确认授权",
      success: async ({ confirm }) => {
        if (!confirm) return;
        await request({
          url: `/admin/users/${archiveId}/role`,
          method: "PUT",
          data: { role }
        });
        this.setData({
          userGrant: { archiveId: "", roleCode: "", roleName: "" }
        });
        wx.showToast({ title: "授权成功", icon: "success" });
      }
    });
  },

  openRoleCreate() {
    this.setData({ roleCreateVisible: true });
  },

  closeRoleCreate() {
    this.setData({ roleCreateVisible: false });
  },

  openPermissionCreate() {
    this.setData({ permissionCreateVisible: true });
  },

  closePermissionCreate() {
    this.setData({ permissionCreateVisible: false });
  },

  preventModalClose() {},

  async handleRbacEnabled(event) {
    const scope = event.currentTarget.dataset.scope;
    const index = Number(event.currentTarget.dataset.index);
    const enabled = event.detail.value;
    this.setData({ [`${scope}[${index}].enabled`]: enabled });
    const item = this.data[scope][index];
    try {
      if (scope === "roles") {
        await request({
          url: `/admin/roles/${item.code}`,
          method: "PUT",
          data: {
            name: item.name.trim(),
            description: item.description ? item.description.trim() : null,
            rank: Number(item.rank) || 0,
            enabled
          }
        });
      } else {
        await request({
          url: `/admin/permissions/${item.code}`,
          method: "PUT",
          data: {
            name: item.name.trim(),
            description: item.description ? item.description.trim() : null,
            module: item.module.trim() || "general",
            enabled
          }
        });
      }
      wx.showToast({ title: enabled ? "已启用" : "已停用", icon: "success" });
      await this.loadRbac();
    } catch (error) {
      await this.loadRbac();
    }
  },

  toggleRbacItem(event) {
    const scope = event.currentTarget.dataset.scope;
    const index = Number(event.currentTarget.dataset.index);
    const current = Boolean(this.data[scope][index].expanded);
    this.setData({ [`${scope}[${index}].expanded`]: !current });
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
      newRole: { code: "", name: "", description: "", rank: 0 },
      roleCreateVisible: false
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
      },
      permissionCreateVisible: false
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
    wx.showModal({
      title: "发送管理员消息",
      editable: true,
      placeholderText: "请输入回复内容",
      content: "",
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

  deleteFeedback(event) {
    const id = Number(event.currentTarget.dataset.id);
    wx.showModal({
      title: "删除反馈",
      content: "确定删除这条反馈信息？删除后该反馈和下方所有对话记录将不再展示，且不能恢复。",
      confirmText: "确定删除",
      confirmColor: "#E5484D",
      success: async ({ confirm }) => {
        if (!confirm) return;
        this.setData({ deletingFeedbackId: id });
        try {
          await request({
            url: `/admin/feedback/${id}`,
            method: "DELETE"
          });
          wx.showToast({ title: "反馈已删除", icon: "success" });
          await this.loadFeedback();
        } finally {
          this.setData({ deletingFeedbackId: 0 });
        }
      }
    });
  },

  revokeFeedbackReply(event) {
    const id = Number(event.currentTarget.dataset.id);
    const messageId = Number(event.currentTarget.dataset.messageId);
    wx.showModal({
      title: "撤销管理员回复",
      content: "确定撤销这条管理员回复？撤销后用户将不再看到该回复，且不能恢复。",
      confirmText: "确定撤销",
      confirmColor: "#E5484D",
      success: async ({ confirm }) => {
        if (!confirm) return;
        this.setData({ revokingReplyId: messageId });
        try {
          await request({
            url: `/admin/feedback/${id}/messages/${messageId}`,
            method: "DELETE"
          });
          wx.showToast({ title: "回复已撤销", icon: "success" });
          this.setData({ status: "pending", page: 1 });
          await this.loadFeedback();
        } finally {
          this.setData({ revokingReplyId: 0 });
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
