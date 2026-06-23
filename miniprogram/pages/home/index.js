const { request, uploadImage } = require("../../utils/request");
const {
  formatDate,
  formatDateTimeSeconds,
  oneYearAgo
} = require("../../utils/date");
const { normalizeOcrResult } = require("../../utils/ocr");

const DAILY_ENCOURAGEMENTS = [
  "认真记录每一次变化，也是在认真照顾自己。",
  "规律一点点，安心多一点点。",
  "愿今天的你，平稳、从容、心情舒展。",
  "照顾好身体，也别忘了照顾好心情。",
  "每一次记录，都是送给未来自己的安心。",
  "慢一点没关系，坚持就是很好的进步。",
  "愿你三餐规律，睡眠安稳，日日心安。",
  "把日子过得从容些，把自己照顾得周全些。",
  "今天也要记得喝水、休息，好好爱自己。",
  "愿清晨有期待，夜晚有好眠，心中有安宁。",
  "身体需要呵护，心情也值得被温柔安放。",
  "每一个认真生活的今天，都在积攒明天的安心。",
  "不用急着赶路，稳稳走好每一步就很好。",
  "愿你的生活有规律，心里有阳光，身边有温暖。",
  "好好吃饭，好好睡觉，就是朴素又重要的幸福。",
  "今天辛苦了，也请给自己一点休息的时间。",
  "愿你忙而不乱，累而知休，日日自在。",
  "照顾自己不是任务，是送给自己的温柔。",
  "愿你的每一天，都比昨天多一点轻松。",
  "保持记录，也保持对生活的小小期待。",
  "不必事事完美，身体舒服、内心安稳就很好。",
  "给身体一点耐心，也给自己一点鼓励。",
  "愿今天有好心情，也有恰到好处的好状态。",
  "一点一滴的好习惯，会悄悄带来踏实和安心。",
  "愿你认真生活，也能轻松生活。",
  "停下来歇一歇，也是继续向前的一部分。",
  "愿你所遇皆温柔，所行皆从容。",
  "每天关心自己一点，生活就会温柔一点。",
  "愿平安常伴左右，喜乐常在心间。",
  "愿每一次呼吸都从容，每一个日子都有暖意。"
];

function getRandomEncouragement() {
  const index = Math.floor(Math.random() * DAILY_ENCOURAGEMENTS.length);
  return DAILY_ENCOURAGEMENTS[index];
}

Page({
  data: {
    imagePath: "",
    ocrLoading: false,
    ocrNotice: "",
    ocrEngine: "rapid",
    cloudOcrConsent: false,
    canCloudOcr: false,
    ocrEngines: [
      {
        value: "rapid",
        label: "快速识别",
        description: "本地处理，速度快"
      },
      {
        value: "doubao",
        label: "增强识别",
        description: "豆包视觉 AI，复杂图片效果更好"
      },
      {
        value: "auto",
        label: "智能识别",
        description: "快速优先，必要时自动增强"
      }
    ],
    submitting: false,
    notePromptVisible: false,
    noteDraft: "",
    dailyEncouragement: getRandomEncouragement(),
    trendLoading: false,
    form: {
      systolic: "",
      diastolic: "",
      heartRate: "",
      measuredDate: formatDate(new Date())
    },
    dimensions: [
      { label: "按日", value: "day" },
      { label: "按月", value: "month" },
      { label: "按年", value: "year" }
    ],
    dimension: "month",
    startDate: oneYearAgo(),
    endDate: formatDate(new Date()),
    trendPoints: [],
    summary: {},
    records: [],
    recordTotal: 0,
    recordsModalVisible: false,
    allRecordsLoading: false,
    allRecords: [],
    recordsPage: 1,
    recordsPageSize: 10,
    recordsTotal: 0,
    recordsTotalPages: 1,
    recordFilterMaxDate: formatDate(new Date()),
    recordFilters: {
      startTime: "",
      endTime: ""
    },
    editVisible: false,
    editSaving: false,
    editForm: {
      id: null,
      systolic: "",
      diastolic: "",
      heartRate: "",
      measuredAt: "",
      note: ""
    }
  },

  onLoad() {
    this.loadAccess();
    this.refreshPage();
  },

  onShow() {
    this.setData({ dailyEncouragement: getRandomEncouragement() });
    const tabBar = this.getTabBar && this.getTabBar();
    if (tabBar) {
      tabBar.setData({ selected: 0 });
      if (tabBar.refreshUnreadCount) tabBar.refreshUnreadCount();
    }
    if (this.data.hasLoaded) this.loadRecords();
    this.loadAccess();
  },

  async loadAccess() {
    try {
      const access = await getApp().refreshAccess();
      this.setData({
        canCloudOcr: (access.permissions || []).includes("cloud_ocr")
      });
    } catch (error) {
      this.setData({ canCloudOcr: false });
    }
  },

  onHide() {
    this.setData({
      ocrEngine: "rapid",
      cloudOcrConsent: false
    });
  },

  onPullDownRefresh() {
    this.refreshPage().finally(() => wx.stopPullDownRefresh());
  },

  async refreshPage() {
    await this.loadRecords();
    this.setData({ hasLoaded: true });
  },

  openHealthRecord() {
    wx.navigateTo({ url: "/pages/health-record/index" });
  },

  selectOcrEngine(event) {
    const engine = event.currentTarget.dataset.value;
    if (engine === this.data.ocrEngine) return;
    if (engine !== "rapid" && !this.data.canCloudOcr) {
      wx.showModal({
        title: "会员功能",
        content: "当前账号暂无 AI 智能图片识别权限，请前往“我的”查看可开通的会员服务。",
        confirmText: "前往查看",
        success: ({ confirm }) => {
          if (confirm) wx.switchTab({ url: "/pages/profile/index" });
        }
      });
      return;
    }
    const cloudOcrPrompt = engine === "doubao"
      ? {
          title: "使用豆包增强识别",
          content: "图片将发送至火山引擎豆包 AI，仅用于识别血压数据。是否继续？"
        }
      : {
          title: "使用智能识别",
          content: "必要时图片将发送至火山引擎豆包 AI，辅助识别血压数据。是否继续？"
        };
    if (
      engine !== "rapid" &&
      !this.data.cloudOcrConsent
    ) {
      wx.showModal({
        title: cloudOcrPrompt.title,
        content: cloudOcrPrompt.content,
        confirmText: "确认使用",
        success: ({ confirm }) => {
          if (!confirm) return;
          this.setData({
            ocrEngine: engine,
            cloudOcrConsent: true
          });
        }
      });
      return;
    }
    this.setData({ ocrEngine: engine });
  },

  chooseImage() {
    if (this.data.ocrLoading) return;
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["camera", "album"],
      sizeType: ["compressed"],
      success: ({ tempFiles }) => {
        const imagePath = tempFiles[0].tempFilePath;
        this.setData({ imagePath });
        this.recognizeImage(imagePath);
      }
    });
  },

  async recognizeImage(imagePath) {
    this.setData({ ocrLoading: true, ocrNotice: "" });
    try {
      const response = await uploadImage(imagePath, this.data.ocrEngine);
      const result = normalizeOcrResult(response);
      const notice = result.complete
        ? (result.notice || "识别完成，请核对数值后保存。")
        : result.hasAnyValue
          ? "仅识别到部分数值，请核对并补充空白项。"
          : "未识别到有效数值，请重新拍摄或手动填写。";

      this.setData({
        "form.systolic": result.systolic,
        "form.diastolic": result.diastolic,
        "form.heartRate": result.heartRate,
        ocrNotice: notice
      });
      console.info("OCR result", {
        systolic: result.systolic,
        diastolic: result.diastolic,
        heartRate: result.heartRate,
        rawText: result.rawText,
        engine: result.engine,
        provider: result.provider,
        fallbackUsed: result.fallbackUsed
      });
      wx.showToast({
        title: result.complete ? "识别完成" : "请核对识别结果",
        icon: result.complete ? "success" : "none"
      });
    } catch (error) {
      const message = error && error.message
        ? error.message
        : "未能完整识别，请手动填写或重新拍摄。";
      this.setData({ ocrNotice: message });
      console.error("OCR failed", error);
    } finally {
      this.setData({ ocrLoading: false });
    }
  },

  handleInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`form.${field}`]: event.detail.value });
  },

  handleDateChange(event) {
    this.setData({ "form.measuredDate": event.detail.value });
  },

  validateForm() {
    const { systolic, diastolic, heartRate } = this.data.form;
    const high = Number(systolic);
    const low = Number(diastolic);
    const heart = heartRate ? Number(heartRate) : null;
    if (!high || high < 50 || high > 260) return "请输入 50～260 的高压";
    if (!low || low < 30 || low > 180) return "请输入 30～180 的低压";
    if (high <= low) return "高压应大于低压";
    if (heart && (heart < 30 || heart > 220)) return "请输入 30～220 的心率";
    return "";
  },

  requestRecordNote() {
    return new Promise((resolve) => {
      this.notePromptResolver = resolve;
      this.setData({
        notePromptVisible: true,
        noteDraft: ""
      });
    });
  },

  handleNoteDraftInput(event) {
    this.setData({ noteDraft: event.detail.value });
  },

  closeNotePrompt() {
    const resolve = this.notePromptResolver;
    this.notePromptResolver = null;
    this.setData({
      notePromptVisible: false,
      noteDraft: ""
    });
    if (resolve) resolve(null);
  },

  confirmNotePrompt() {
    const resolve = this.notePromptResolver;
    const note = String(this.data.noteDraft || "").trim();
    this.notePromptResolver = null;
    this.setData({
      notePromptVisible: false,
      noteDraft: ""
    });
    if (resolve) resolve(note);
  },

  preventModalClose() {},

  async submitRecord() {
    const message = this.validateForm();
    if (message) {
      wx.showToast({ title: message, icon: "none" });
      return;
    }
    if (this.data.submitting || this.data.notePromptVisible) return;
    const note = await this.requestRecordNote();
    if (note === null) return;
    this.setData({ submitting: true });
    const form = this.data.form;
    try {
      const response = await request({
        url: "/blood-pressure",
        method: "POST",
        data: {
          systolic: Number(form.systolic),
          diastolic: Number(form.diastolic),
          heart_rate: form.heartRate ? Number(form.heartRate) : null,
          measured_at: `${form.measuredDate}T${new Date().toTimeString().slice(0, 8)}`,
          note: note || null
        }
      });
      wx.showToast({ title: response.message || "保存成功", icon: "success" });
      this.setData({
        imagePath: "",
        ocrNotice: "",
        "form.systolic": "",
        "form.diastolic": "",
        "form.heartRate": ""
      });
      await this.loadRecords();
      const tabBar = this.getTabBar && this.getTabBar();
      if (tabBar && tabBar.refreshUnreadCount) {
        await tabBar.refreshUnreadCount();
      }
    } finally {
      this.setData({ submitting: false });
    }
  },

  changeDimension(event) {
    const dimension = event.currentTarget.dataset.value;
    this.setData({ dimension }, () => this.loadTrend());
  },

  changeStartDate(event) {
    this.setData({ startDate: event.detail.value });
  },

  changeEndDate(event) {
    this.setData({ endDate: event.detail.value });
  },

  async loadTrend() {
    if (this.data.startDate > this.data.endDate) {
      wx.showToast({ title: "开始日期不能晚于结束日期", icon: "none" });
      return;
    }
    this.setData({ trendLoading: true });
    try {
      const response = await request({
        url: "/blood-pressure/trend",
        data: {
          dimension: this.data.dimension,
          start_date: `${this.data.startDate}T00:00:00`,
          end_date: `${this.data.endDate}T23:59:59`
        },
        silent: true
      });
      const data = response.data || {};
      this.setData({
        trendPoints: data.points || [],
        summary: data.summary || {}
      }, () => this.drawChart());
    } catch (error) {
      this.setData({ trendPoints: [], summary: {} });
    } finally {
      this.setData({ trendLoading: false });
    }
  },

  async loadRecords() {
    try {
      const response = await request({
        url: "/blood-pressure",
        data: { page: 1, page_size: 3 },
        silent: true
      });
      const data = response.data || {};
      const records = (data.items || []).map((item) => ({
        ...item,
        displayTime: formatDateTimeSeconds(item.created_at),
        compactTime: formatDateTimeSeconds(item.created_at).slice(5, 16)
      }));
      this.setData({ records, recordTotal: data.total || 0 });
    } catch (error) {
      this.setData({ records: [], recordTotal: 0 });
    }
  },

  noop() {},

  openRecordsModal() {
    this.setData({
      recordsModalVisible: true,
      recordsPage: 1,
      editVisible: false
    }, () => this.loadAllRecords());
  },

  closeRecordsModal() {
    if (this.data.editSaving) return;
    this.setData({
      recordsModalVisible: false,
      editVisible: false
    });
  },

  changeRecordStartDate(event) {
    this.setData({ "recordFilters.startTime": event.detail.value });
  },

  changeRecordEndDate(event) {
    this.setData({ "recordFilters.endTime": event.detail.value });
  },

  normalizeQueryTime(value, boundary) {
    const text = String(value || "").trim();
    if (!text) return "";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
      throw new Error("请选择有效日期");
    }
    const time = boundary === "end" ? "23:59:59" : "00:00:00";
    const dateTime = `${text}T${time}`;
    const date = new Date(dateTime);
    if (Number.isNaN(date.getTime())) {
      throw new Error("请选择有效日期");
    }
    return dateTime;
  },

  queryAllRecords() {
    this.setData({ recordsPage: 1 }, () => this.loadAllRecords());
  },

  resetRecordFilters() {
    this.setData({
      recordFilters: { startTime: "", endTime: "" },
      recordsPage: 1
    }, () => this.loadAllRecords());
  },

  async loadAllRecords() {
    if (this.data.allRecordsLoading) return;
    let startTime = "";
    let endTime = "";
    try {
      startTime = this.normalizeQueryTime(
        this.data.recordFilters.startTime,
        "start"
      );
      endTime = this.normalizeQueryTime(
        this.data.recordFilters.endTime,
        "end"
      );
      if (startTime && endTime && startTime > endTime) {
        throw new Error("开始时间不能晚于结束时间");
      }
    } catch (error) {
      wx.showToast({ title: error.message, icon: "none" });
      return;
    }

    this.setData({ allRecordsLoading: true });
    try {
      const response = await request({
        url: "/blood-pressure",
        data: {
          page: this.data.recordsPage,
          page_size: this.data.recordsPageSize,
          ...(startTime ? { start_time: startTime } : {}),
          ...(endTime ? { end_time: endTime } : {})
        }
      });
      const data = response.data || {};
      const allRecords = (data.items || []).map((item) => ({
        ...item,
        displayTime: formatDateTimeSeconds(item.created_at)
      }));
      this.setData({
        allRecords,
        recordsTotal: data.total || 0,
        recordsTotalPages: data.total_pages || 1
      });
    } finally {
      this.setData({ allRecordsLoading: false });
    }
  },

  previousRecordsPage() {
    if (this.data.recordsPage <= 1 || this.data.allRecordsLoading) return;
    this.setData({
      recordsPage: this.data.recordsPage - 1
    }, () => this.loadAllRecords());
  },

  nextRecordsPage() {
    if (
      this.data.recordsPage >= this.data.recordsTotalPages ||
      this.data.allRecordsLoading
    ) return;
    this.setData({
      recordsPage: this.data.recordsPage + 1
    }, () => this.loadAllRecords());
  },

  openEditRecord(event) {
    const id = Number(event.currentTarget.dataset.id);
    const record = this.data.allRecords.find((item) => item.id === id);
    if (!record) return;
    this.setData({
      editVisible: true,
      editForm: {
        id: record.id,
        systolic: String(record.systolic),
        diastolic: String(record.diastolic),
        heartRate: record.heart_rate ? String(record.heart_rate) : "",
        measuredAt: formatDateTimeSeconds(record.created_at),
        note: record.note || ""
      }
    });
  },

  closeEditRecord() {
    if (!this.data.editSaving) {
      this.setData({ editVisible: false });
    }
  },

  handleEditInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`editForm.${field}`]: event.detail.value });
  },

  validateEditForm() {
    const form = this.data.editForm;
    const systolic = Number(form.systolic);
    const diastolic = Number(form.diastolic);
    const heartRate = form.heartRate ? Number(form.heartRate) : null;
    if (!systolic || systolic < 50 || systolic > 260) return "高压范围应为 50～260";
    if (!diastolic || diastolic < 30 || diastolic > 180) return "低压范围应为 30～180";
    if (systolic <= diastolic) return "高压应大于低压";
    if (heartRate && (heartRate < 30 || heartRate > 220)) return "心率范围应为 30～220";
    return "";
  },

  async saveEditedRecord() {
    const errorMessage = this.validateEditForm();
    if (errorMessage) {
      wx.showToast({ title: errorMessage, icon: "none" });
      return;
    }
    if (this.data.editSaving) return;
    this.setData({ editSaving: true });
    const form = this.data.editForm;
    try {
      await request({
        url: `/blood-pressure/${form.id}`,
        method: "PUT",
        data: {
          systolic: Number(form.systolic),
          diastolic: Number(form.diastolic),
          heart_rate: form.heartRate ? Number(form.heartRate) : null,
          note: form.note || null
        }
      });
      wx.showToast({ title: "记录更新成功", icon: "success" });
      this.setData({ editVisible: false });
      await Promise.all([
        this.loadAllRecords(),
        this.loadRecords(),
        this.loadTrend()
      ]);
    } finally {
      this.setData({ editSaving: false });
    }
  },

  deleteRecord(event) {
    const id = Number(event.currentTarget.dataset.id);
    const record = this.data.allRecords.find((item) => item.id === id);
    if (!record) return;
    wx.showModal({
      title: "确认删除",
      content: `确定删除 ${record.displayTime} 的血压记录吗？删除后无法恢复。`,
      confirmText: "删除",
      confirmColor: "#F53F3F",
      success: async (result) => {
        if (!result.confirm) return;
        try {
          await request({
            url: `/blood-pressure/${id}`,
            method: "DELETE"
          });
          wx.showToast({ title: "已删除", icon: "success" });
          const nextTotal = Math.max(0, this.data.recordsTotal - 1);
          const nextTotalPages = Math.max(
            1,
            Math.ceil(nextTotal / this.data.recordsPageSize)
          );
          const nextPage = Math.min(this.data.recordsPage, nextTotalPages);
          this.setData({ recordsPage: nextPage });
          await Promise.all([
            this.loadAllRecords(),
            this.loadRecords(),
            this.loadTrend()
          ]);
        } catch (error) {
          // request 已统一展示错误。
        }
      }
    });
  },

  drawChart() {
    const points = this.data.trendPoints;
    if (!points.length) return;
    const query = wx.createSelectorQuery();
    query.select(".trend-chart").boundingClientRect((rect) => {
      if (!rect) return;
      const width = rect.width;
      const height = rect.height;
      const ctx = wx.createCanvasContext("trendChart", this);
      const padding = { left: 40, right: 16, top: 20, bottom: 35 };
      const chartWidth = width - padding.left - padding.right;
      const chartHeight = height - padding.top - padding.bottom;
      const allValues = points.reduce((values, point) => {
        return values.concat([point.systolic, point.diastolic, point.heart_rate].filter(Boolean));
      }, []);
      const minValue = Math.max(0, Math.floor(Math.min(...allValues) / 20) * 20 - 20);
      const maxValue = Math.ceil(Math.max(...allValues) / 20) * 20 + 20;
      const range = Math.max(maxValue - minValue, 1);

      ctx.setStrokeStyle("#E5E6EB");
      ctx.setLineWidth(1);
      ctx.setFontSize(10);
      ctx.setFillStyle("#86909C");
      for (let index = 0; index <= 4; index += 1) {
        const y = padding.top + (chartHeight / 4) * index;
        const value = Math.round(maxValue - (range / 4) * index);
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.fillText(String(value), 4, y + 3);
      }

      const step = points.length > 1 ? chartWidth / (points.length - 1) : 0;
      const series = [
        { field: "systolic", color: "#1677FF" },
        { field: "diastolic", color: "#52C41A" },
        { field: "heart_rate", color: "#FA8C16" }
      ];
      series.forEach(({ field, color }) => {
        ctx.setStrokeStyle(color);
        ctx.setFillStyle(color);
        ctx.setLineWidth(2);
        ctx.beginPath();
        points.forEach((point, index) => {
          if (point[field] === null || point[field] === undefined) return;
          const x = padding.left + (points.length === 1 ? chartWidth / 2 : step * index);
          const y = padding.top + ((maxValue - point[field]) / range) * chartHeight;
          if (index === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
        points.forEach((point, index) => {
          if (point[field] === null || point[field] === undefined) return;
          const x = padding.left + (points.length === 1 ? chartWidth / 2 : step * index);
          const y = padding.top + ((maxValue - point[field]) / range) * chartHeight;
          ctx.beginPath();
          ctx.arc(x, y, 2.5, 0, Math.PI * 2);
          ctx.fill();
        });
      });

      const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
      ctx.setFillStyle("#86909C");
      ctx.setFontSize(9);
      labelIndexes.forEach((index) => {
        const x = padding.left + (points.length === 1 ? chartWidth / 2 : step * index);
        const label = points[index].label;
        ctx.fillText(label, Math.max(2, x - 18), height - 10);
      });
      ctx.draw();
    }).exec();
  }
});
