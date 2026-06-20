const { request, uploadImage } = require("../../utils/request");
const { formatDate, formatDateTime, oneYearAgo } = require("../../utils/date");

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
    recordTotal: 0
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
      const result = response.data || {};
      this.setData({
        "form.systolic": result.systolic || "",
        "form.diastolic": result.diastolic || "",
        "form.heartRate": result.heart_rate || "",
        ocrNotice: result.notice || "识别完成，请核对数值后保存。"
      });
      wx.showToast({ title: "识别完成", icon: "success" });
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
        data: { page: 1, page_size: 5 },
        silent: true
      });
      const data = response.data || {};
      const records = (data.items || []).map((item) => ({
        ...item,
        displayTime: formatDateTime(item.created_at)
      }));
      this.setData({ records, recordTotal: data.total || 0 });
    } catch (error) {
      this.setData({ records: [], recordTotal: 0 });
    }
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

