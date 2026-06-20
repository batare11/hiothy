const { request, uploadImage } = require("../../utils/request");
const {
  formatDate,
  formatDateTimeSeconds,
  oneYearAgo
} = require("../../utils/date");
const { normalizeOcrResult } = require("../../utils/ocr");

Page({
  data: {
    imagePath: "",
    ocrLoading: false,
    ocrNotice: "",
    submitting: false,
    trendLoading: false,
    form: {
      systolic: "",
      diastolic: "",
      heartRate: "",
      measuredDate: formatDate(new Date()),
      note: ""
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
    this.refreshPage();
  },

  onShow() {
    if (this.data.hasLoaded) this.loadRecords();
  },

  onPullDownRefresh() {
    this.refreshPage().finally(() => wx.stopPullDownRefresh());
  },

  async refreshPage() {
    await Promise.all([this.loadTrend(), this.loadRecords()]);
    this.setData({ hasLoaded: true });
  },

  openHealthRecord() {
    wx.navigateTo({ url: "/pages/health-record/index" });
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
      const response = await uploadImage(imagePath);
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
        rawText: result.rawText
      });
      wx.showToast({
        title: result.complete ? "识别完成" : "请核对识别结果",
        icon: result.complete ? "success" : "none"
      });
    } catch (error) {
      this.setData({ ocrNotice: "未能完整识别，请手动填写或重新拍摄。" });
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

  async submitRecord() {
    const message = this.validateForm();
    if (message) {
      wx.showToast({ title: message, icon: "none" });
      return;
    }
    if (this.data.submitting) return;
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
          note: form.note || null
        }
      });
      wx.showToast({ title: response.message || "保存成功", icon: "success" });
      this.setData({
        imagePath: "",
        ocrNotice: "",
        "form.systolic": "",
        "form.diastolic": "",
        "form.heartRate": "",
        "form.note": ""
      });
      await Promise.all([this.loadTrend(), this.loadRecords()]);
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
        displayTime: formatDateTimeSeconds(item.created_at)
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

  handleFilterInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`recordFilters.${field}`]: event.detail.value });
  },

  normalizeQueryTime(value) {
    const text = String(value || "").trim();
    if (!text) return "";
    if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(text)) {
      throw new Error("时间格式应为 YYYY-MM-DD HH:mm:ss");
    }
    const date = new Date(text.replace(" ", "T"));
    if (Number.isNaN(date.getTime())) {
      throw new Error("请输入有效时间");
    }
    return text.replace(" ", "T");
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
      startTime = this.normalizeQueryTime(this.data.recordFilters.startTime);
      endTime = this.normalizeQueryTime(this.data.recordFilters.endTime);
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
