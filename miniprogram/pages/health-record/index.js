const { request } = require("../../utils/request");
const { formatDate, formatDateTimeSeconds } = require("../../utils/date");

function calculateBmiProfile(heightCm, weightJin) {
  const height = Number(heightCm);
  const weight = Number(weightJin);
  if (!height || !weight) {
    return {
      value: "",
      label: "补资料",
      status: "missing"
    };
  }

  const value = weight / 2 / ((height / 100) ** 2);
  if (value < 18.5) {
    return { value: value.toFixed(1), label: "偏瘦", status: "low" };
  }
  if (value < 24) {
    return { value: value.toFixed(1), label: "正常", status: "normal" };
  }
  if (value < 28) {
    return { value: value.toFixed(1), label: "超重", status: "elevated" };
  }
  return { value: value.toFixed(1), label: "肥胖", status: "danger" };
}

function normalizeArchive(archive) {
  return {
    age: archive.age == null ? "" : archive.age,
    height_cm: archive.height_cm == null ? "" : archive.height_cm,
    weight_jin: archive.weight_jin == null ? "" : archive.weight_jin,
    gender: archive.gender == null ? null : Number(archive.gender),
    marital_status: archive.marital_status == null
      ? null
      : Number(archive.marital_status),
    smoking: Boolean(archive.smoking),
    drinking: Boolean(archive.drinking),
    staying_up_late: Boolean(archive.staying_up_late),
    note: archive.note || ""
  };
}

function getMissingArchiveFields(archive) {
  const fields = [
    ["年龄", archive.age !== "" && archive.age != null],
    ["身高", archive.height_cm !== "" && archive.height_cm != null],
    ["体重", archive.weight_jin !== "" && archive.weight_jin != null],
    ["性别", archive.gender !== null && archive.gender !== undefined],
    [
      "婚姻状态",
      archive.marital_status !== null &&
        archive.marital_status !== undefined
    ]
  ];
  return fields.filter(([, completed]) => !completed).map(([label]) => label);
}

Page({
  data: {
    loading: false,
    overview: {
      total: 0,
      record_days: 0,
      normal_rate: 0,
      abnormal_count: 0,
      abnormal_rate: 0,
      recent_7_days: {},
      averages: {},
      latest: null,
      monthly: [],
      firstRecordText: "",
      latestTime: ""
    },
    archive: {
      age: "",
      height_cm: "",
      weight_jin: "",
      gender: null,
      marital_status: null,
      smoking: false,
      drinking: false,
      staying_up_late: false,
      note: ""
    },
    bmi: calculateBmiProfile(null, null),
    savingArchive: false,
    archiveSavedSnapshot: "",
    archiveDirty: false,
    aiReportLoading: false,
    aiReportVisible: false,
    aiReport: "",
    aiReportModel: "",
    canAiHealthReport: false
  },

  onLoad() {
    this.loadAccess();
    this.loadOverview();
  },

  async loadAccess() {
    try {
      const access = await getApp().refreshAccess();
      this.setData({
        canAiHealthReport: (access.permissions || []).includes("ai_health_report")
      });
    } catch (error) {
      this.setData({ canAiHealthReport: false });
    }
  },

  onPullDownRefresh() {
    this.loadOverview().finally(() => wx.stopPullDownRefresh());
  },

  async loadOverview() {
    this.setData({ loading: true });
    try {
      const [overviewResponse, archiveResponse] = await Promise.all([
        request({ url: "/blood-pressure/overview" }),
        request({ url: "/health-archive" })
      ]);
      const data = overviewResponse.data || {};
      const archive = archiveResponse.data || {};
      const bmi = calculateBmiProfile(
        archive.height_cm,
        archive.weight_jin
      );
      const normalizedArchive = normalizeArchive(archive);
      this.setData({
        overview: {
          ...data,
          averages: data.averages || {},
          recent_7_days: data.recent_7_days || {},
          monthly: data.monthly || [],
          firstRecordText: data.first_record_at
            ? formatDate(data.first_record_at)
            : "",
          latestTime: data.latest
            ? formatDateTimeSeconds(data.latest.created_at)
            : ""
        },
        archive: normalizedArchive,
        bmi,
        archiveSavedSnapshot: JSON.stringify(normalizedArchive),
        archiveDirty: false
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  buildMedicalSummary() {
    const data = this.data.overview;
    const archive = this.data.archive;
    const latest = data.latest;
    const averages = data.averages || {};
    const recentWeek = data.recent_7_days || {};
    const height = Number(archive.height_cm);
    const weightJin = Number(archive.weight_jin);
    const bmi = calculateBmiProfile(height, weightJin);
    const habits = [
      archive.smoking ? "吸烟" : "不吸烟",
      archive.drinking ? "饮酒" : "不饮酒",
      archive.staying_up_late ? "经常熬夜" : "无经常熬夜"
    ].join("，");
    return [
      "血压健康档案摘要",
      `统计时间：${formatDateTimeSeconds(new Date())}`,
      "",
      "【基础健康资料】",
      `性别：${archive.gender == null ? "未填写" : archive.gender === 1 ? "男" : "女"}`,
      `年龄：${archive.age === "" ? "--" : archive.age} 岁`,
      `婚姻状况：${archive.marital_status == null ? "未填写" : archive.marital_status === 1 ? "已婚" : "未婚"}`,
      `身高：${archive.height_cm || "--"} cm`,
      `体重：${archive.weight_jin || "--"} 斤${
        bmi.value ? `，BMI ${bmi.value}（${bmi.label}）` : ""
      }`,
      `生活习惯：${habits}`,
      `补充备注：${archive.note.trim() || "无"}`,
      "",
      "【血压记录】",
      `首次记录：${data.firstRecordText || "暂无"}`,
      `累计记录天数：${data.record_days || 0} 天`,
      `累计记录：${data.total || 0} 次`,
      `正常率：${data.normal_rate || 0}%`,
      `异常率：${data.abnormal_rate || 0}%（${data.abnormal_count || 0} 次）`,
      `历史平均：高压 ${averages.systolic || "--"} mmHg，低压 ${averages.diastolic || "--"} mmHg，心率 ${averages.heart_rate || "--"} 次/分`,
      latest
        ? `最近测量：${data.latestTime}，${latest.systolic}/${latest.diastolic} mmHg，心率 ${latest.heart_rate || "--"} 次/分，状态：${latest.status_text}`
        : "最近测量：暂无",
      "",
      "【最近7天分析】",
      `测量次数：${recentWeek.total || 0} 次`,
      `平均血压：高压 ${recentWeek.avg_systolic || "--"} mmHg，低压 ${recentWeek.avg_diastolic || "--"} mmHg`,
      `平均心率：${recentWeek.avg_heart_rate || "--"} 次/分`,
      `正常记录：${recentWeek.normal_count || 0} 次，异常记录：${recentWeek.abnormal_count || 0} 次`,
      `正常率：${recentWeek.normal_rate || 0}%，异常率：${recentWeek.abnormal_rate || 0}%`,
      "",
      "说明：以上数据仅供健康管理参考，不作为医疗诊断依据。"
    ].join("\n");
  },

  handleArchiveInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({
      [`archive.${field}`]: event.detail.value,
      archiveDirty: true
    });
  },

  selectGender(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({
      "archive.gender": value,
      archiveDirty: true
    });
  },

  selectMaritalStatus(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({
      "archive.marital_status": value,
      archiveDirty: true
    });
  },

  changeHabit(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({
      [`archive.${field}`]: event.detail.value,
      archiveDirty: true
    });
  },

  async saveArchive() {
    if (this.data.savingArchive) return;
    const age = this.data.archive.age === ""
      ? null
      : Number(this.data.archive.age);
    const height = this.data.archive.height_cm === ""
      ? null
      : Number(this.data.archive.height_cm);
    const weight = this.data.archive.weight_jin === ""
      ? null
      : Number(this.data.archive.weight_jin);
    if (age !== null && (!Number.isInteger(age) || age < 0 || age > 150)) {
      wx.showToast({ title: "年龄应为 0～150 岁", icon: "none" });
      return;
    }
    if (height !== null && (!Number.isFinite(height) || height < 50 || height > 250)) {
      wx.showToast({ title: "身高应为 50～250 cm", icon: "none" });
      return;
    }
    if (weight !== null && (!Number.isFinite(weight) || weight < 20 || weight > 500)) {
      wx.showToast({ title: "体重应为 20～500 斤", icon: "none" });
      return;
    }
    this.setData({ savingArchive: true });
    try {
      const response = await request({
        url: "/health-archive",
        method: "PUT",
        data: {
          ...this.data.archive,
          age,
          height_cm: height,
          weight_jin: weight,
          gender: this.data.archive.gender,
          marital_status: this.data.archive.marital_status,
          note: this.data.archive.note.trim() || null
        }
      });
      const archive = response.data || {};
      const normalizedArchive = normalizeArchive(archive);
      this.setData({
        archive: normalizedArchive,
        bmi: calculateBmiProfile(archive.height_cm, archive.weight_jin),
        archiveSavedSnapshot: JSON.stringify(normalizedArchive),
        archiveDirty: false
      });
      wx.showToast({ title: "档案已保存", icon: "success" });
    } finally {
      this.setData({ savingArchive: false });
    }
  },

  ensureArchiveReady() {
    const missingFields = getMissingArchiveFields(this.data.archive);
    if (missingFields.length) {
      wx.showModal({
        title: "请先补充档案资料",
        content: `请填写${missingFields.join("、")}并点击“保存辅助档案”后再生成分析。`,
        showCancel: false,
        confirmText: "知道了"
      });
      return false;
    }
    const currentSnapshot = JSON.stringify(
      normalizeArchive(this.data.archive)
    );
    if (
      this.data.archiveDirty ||
      currentSnapshot !== this.data.archiveSavedSnapshot
    ) {
      wx.showModal({
        title: "请先保存档案资料",
        content: "档案资料已修改，请先点击“保存辅助档案”再生成分析。",
        showCancel: false,
        confirmText: "知道了"
      });
      return false;
    }
    return true;
  },

  copyMedicalSummary() {
    if (!this.ensureArchiveReady()) return;
    wx.setClipboardData({
      data: this.buildMedicalSummary(),
      success() {
        wx.showToast({ title: "摘要已复制", icon: "success" });
      }
    });
  },

  generateAiHealthReport() {
    if (this.data.aiReportLoading) return;
    if (!this.data.canAiHealthReport) {
      wx.showModal({
        title: "会员功能",
        content: "当前账号暂无 AI 档案分析权限，请前往“我的”查看可开通的会员服务。",
        confirmText: "前往查看",
        success: ({ confirm }) => {
          if (confirm) wx.switchTab({ url: "/pages/profile/index" });
        }
      });
      return;
    }
    if (!this.ensureArchiveReady()) return;
    wx.showModal({
      title: "生成 AI 健康报告",
      content: "将把个人档案、历史血压和测量备注发送至 DeepSeek V4 Pro 分析。是否继续？",
      confirmText: "确认分析",
      success: async ({ confirm }) => {
        if (!confirm) return;
        this.setData({ aiReportLoading: true });
        try {
          const response = await request({
            url: "/health-archive/ai-report",
            method: "POST",
            timeout: 150000,
            action: "AI 智能分析"
          });
          const data = response.data || {};
          this.setData({
            aiReport: data.report || "",
            aiReportModel: data.model || "deepseek-v4-pro",
            aiReportVisible: true
          });
        } finally {
          this.setData({ aiReportLoading: false });
        }
      }
    });
  },

  closeAiReport() {
    this.setData({ aiReportVisible: false });
  },

  preventModalClose() {},

  copyAiReport() {
    if (!this.data.aiReport) return;
    wx.setClipboardData({
      data: this.data.aiReport,
      success() {
        wx.showToast({ title: "AI 报告已复制", icon: "success" });
      }
    });
  }
});
