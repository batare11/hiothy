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
    }
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
      const response = await request({ url: "/blood-pressure/overview" });
      const data = response.data || {};
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
        }
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  buildMedicalSummary() {
    const data = this.data.overview;
    const latest = data.latest;
    const averages = data.averages || {};
    return [
      "血压健康档案摘要",
      `统计时间：${formatDateTimeSeconds(new Date())}`,
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

  copyMedicalSummary() {
    wx.setClipboardData({
      data: this.buildMedicalSummary(),
      success() {
        wx.showToast({ title: "摘要已复制", icon: "success" });
      }
    });
  }
});
