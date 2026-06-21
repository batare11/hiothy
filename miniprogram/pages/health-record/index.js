const { request } = require("../../utils/request");
const { formatDate, formatDateTimeSeconds } = require("../../utils/date");

Page({
  data: {
    loading: false,
    overview: {
      total: 0,
      normal_rate: 0,
      abnormal_count: 0,
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
    savingArchive: false
  },

  onLoad() {
    this.loadOverview();
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
      this.setData({
        overview: {
          ...data,
          averages: data.averages || {},
          monthly: data.monthly || [],
          firstRecordText: data.first_record_at
            ? formatDate(data.first_record_at)
            : "",
          latestTime: data.latest
            ? formatDateTimeSeconds(data.latest.created_at)
            : ""
        },
        archive: {
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
        }
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
    const height = Number(archive.height_cm);
    const weightJin = Number(archive.weight_jin);
    const bmi = height > 0 && weightJin > 0
      ? (weightJin / 2 / ((height / 100) ** 2)).toFixed(1)
      : "";
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
      `体重：${archive.weight_jin || "--"} 斤${bmi ? `，BMI ${bmi}` : ""}`,
      `生活习惯：${habits}`,
      `补充备注：${archive.note.trim() || "无"}`,
      "",
      "【血压记录】",
      `首次记录：${data.firstRecordText || "暂无"}`,
      `累计记录：${data.total || 0} 次`,
      `正常率：${data.normal_rate || 0}%`,
      `异常记录：${data.abnormal_count || 0} 次`,
      `历史平均：高压 ${averages.systolic || "--"} mmHg，低压 ${averages.diastolic || "--"} mmHg，心率 ${averages.heart_rate || "--"} 次/分`,
      latest
        ? `最近测量：${data.latestTime}，${latest.systolic}/${latest.diastolic} mmHg，心率 ${latest.heart_rate || "--"} 次/分，状态：${latest.status_text}`
        : "最近测量：暂无",
      "",
      "说明：以上数据仅供健康管理参考，不作为医疗诊断依据。"
    ].join("\n");
  },

  handleArchiveInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`archive.${field}`]: event.detail.value });
  },

  selectGender(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({ "archive.gender": value });
  },

  selectMaritalStatus(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({ "archive.marital_status": value });
  },

  changeHabit(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`archive.${field}`]: event.detail.value });
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
      this.setData({
        "archive.age": archive.age == null ? "" : archive.age,
        "archive.height_cm": archive.height_cm == null ? "" : archive.height_cm,
        "archive.weight_jin": archive.weight_jin == null ? "" : archive.weight_jin,
        "archive.note": archive.note || ""
      });
      wx.showToast({ title: "档案已保存", icon: "success" });
    } finally {
      this.setData({ savingArchive: false });
    }
  },

  copyMedicalSummary() {
    wx.setClipboardData({
      data: this.buildMedicalSummary(),
      success() {
        wx.showToast({ title: "摘要已复制", icon: "success" });
      }
    });
  }
});
