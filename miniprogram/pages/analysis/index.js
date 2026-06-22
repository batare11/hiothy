const { request } = require("../../utils/request");
const {
  formatDate,
  formatDateTimeSeconds
} = require("../../utils/date");

const RECORDS_PAGE_SIZE = 10;

function getDefaultTrendRange(dimension) {
  const end = new Date();
  const start = new Date(end);
  const captions = {
    day: "默认展示最近 7 天趋势",
    month: "默认展示最近半年趋势",
    year: "默认展示最近 5 年趋势"
  };

  if (dimension === "day") {
    start.setDate(start.getDate() - 6);
  } else if (dimension === "year") {
    start.setFullYear(start.getFullYear() - 4, 0, 1);
  } else {
    start.setDate(1);
    start.setMonth(start.getMonth() - 5);
  }

  return {
    startDate: formatDate(start),
    endDate: formatDate(end),
    trendCaption: captions[dimension]
  };
}

function parseLocalDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function buildTrendTimeline(dimension, startDate, endDate, sourcePoints) {
  if (dimension === "day" && startDate === endDate) {
    return sourcePoints.map((point) => ({
      ...point,
      axisLabel: point.label
    }));
  }

  const sourceMap = {};
  sourcePoints.forEach((point) => {
    sourceMap[point.label] = point;
  });

  const cursor = parseLocalDate(startDate);
  const end = parseLocalDate(endDate);
  const crossesYear = cursor.getFullYear() !== end.getFullYear();
  if (dimension === "month") cursor.setDate(1);
  if (dimension === "year") cursor.setMonth(0, 1);

  const points = [];
  while (cursor <= end && points.length < 5000) {
    let label = "";
    let axisLabel = "";
    if (dimension === "day") {
      label = formatDate(cursor);
      axisLabel = crossesYear
        ? `${String(cursor.getFullYear()).slice(-2)}.${pad(
            cursor.getMonth() + 1
          )}.${pad(cursor.getDate())}`
        : `${pad(cursor.getMonth() + 1)}-${pad(cursor.getDate())}`;
      cursor.setDate(cursor.getDate() + 1);
    } else if (dimension === "year") {
      label = String(cursor.getFullYear());
      axisLabel = `${label.slice(-2)}年`;
      cursor.setFullYear(cursor.getFullYear() + 1);
    } else {
      label = `${cursor.getFullYear()}-${pad(cursor.getMonth() + 1)}`;
      axisLabel = crossesYear
        ? `${String(cursor.getFullYear()).slice(-2)}.${pad(
            cursor.getMonth() + 1
          )}`
        : `${pad(cursor.getMonth() + 1)}月`;
      cursor.setMonth(cursor.getMonth() + 1);
    }
    points.push({
      label,
      axisLabel,
      systolic: null,
      diastolic: null,
      heart_rate: null,
      count: 0,
      ...(sourceMap[label] || {})
    });
  }
  return points;
}

const initialTrendRange = getDefaultTrendRange("day");

Page({
  data: {
    trendLoading: false,
    dimensions: [
      { label: "按日", value: "day" },
      { label: "按月", value: "month" },
      { label: "按年", value: "year" }
    ],
    dimension: "day",
    startDate: initialTrendRange.startDate,
    endDate: initialTrendRange.endDate,
    trendCaption: initialTrendRange.trendCaption,
    trendPoints: [],
    hasTrendData: false,
    summary: {
      latest_grade: null,
      grade_distribution: []
    },
    gradeStandards: [
      { category: "normal", label: "正常血压", range: "高压 <120 且低压 <80" },
      { category: "high_normal", label: "正常高值", range: "高压 120～139 和/或低压 80～89" },
      { category: "grade_1", label: "高血压1级", range: "高压 140～159 和/或低压 90～99" },
      { category: "grade_2", label: "高血压2级", range: "高压 160～179 和/或低压 100～109" },
      { category: "grade_3", label: "高血压3级", range: "高压 ≥180 和/或低压 ≥110" }
    ],
    records: [],
    recordTotal: 0,
    recordsModalVisible: false,
    allRecordsLoading: false,
    allRecords: [],
    recordsPage: 1,
    recordsPageSize: RECORDS_PAGE_SIZE,
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
    this.refreshPage();
  },

  onShow() {
    const tabBar = this.getTabBar && this.getTabBar();
    if (tabBar) {
      tabBar.setData({ selected: 1 });
      if (tabBar.refreshUnreadCount) tabBar.refreshUnreadCount();
    }
    if (this.data.hasLoaded) this.refreshPage();
  },

  onPullDownRefresh() {
    this.refreshPage().finally(() => wx.stopPullDownRefresh());
  },

  async refreshPage() {
    await Promise.all([this.loadTrend(), this.loadRecords()]);
    this.setData({ hasLoaded: true });
  },

  changeDimension(event) {
    const dimension = event.currentTarget.dataset.value;
    if (dimension === this.data.dimension) return;
    this.setData({
      dimension,
      ...getDefaultTrendRange(dimension)
    }, () => this.loadTrend());
  },

  changeStartDate(event) {
    this.setData({ startDate: event.detail.value });
  },

  changeEndDate(event) {
    this.setData({ endDate: event.detail.value });
  },

  viewTodayTrend() {
    const today = formatDate(new Date());
    this.setData({
      dimension: "day",
      startDate: today,
      endDate: today
    }, () => this.loadTrend());
  },

  viewCurrentMonthByDay() {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    this.setData({
      dimension: "day",
      startDate: formatDate(firstDay),
      endDate: formatDate(lastDay)
    }, () => this.loadTrend());
  },

  resetDayTrend() {
    this.setData({
      dimension: "day",
      ...getDefaultTrendRange("day")
    }, () => this.loadTrend());
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
      const summary = data.summary || {};
      const trendPoints = buildTrendTimeline(
        this.data.dimension,
        this.data.startDate,
        this.data.endDate,
        data.points || []
      );
      this.setData({
        trendPoints,
        hasTrendData: trendPoints.some((item) => item.count > 0),
        summary: {
          ...summary,
          grade_distribution: (summary.grade_distribution || []).map(
            (item) => ({
              ...item,
              barWidth: item.count ? Math.max(item.percent, 4) : 0
            })
          )
        }
      }, () => this.drawChart());
    } catch (error) {
      this.setData({
        trendPoints: [],
        hasTrendData: false,
        summary: { latest_grade: null, grade_distribution: [] }
      });
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
      recordsPageSize: RECORDS_PAGE_SIZE,
      editVisible: false
    }, () => this.loadAllRecords());
  },

  closeRecordsModal() {
    if (this.data.editSaving) return;
    this.setData({
      recordsModalVisible: false,
      editVisible: false
    }, () => {
      wx.nextTick(() => {
        if (this.data.trendPoints.length) this.drawChart();
      });
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
    return `${text}T${boundary === "end" ? "23:59:59" : "00:00:00"}`;
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
      this.setData({
        allRecords: (data.items || []).map((item) => ({
          ...item,
          displayTime: formatDateTimeSeconds(item.created_at)
        })),
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
    if (!this.data.editSaving) this.setData({ editVisible: false });
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
      success: async ({ confirm }) => {
        if (!confirm) return;
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
        this.setData({
          recordsPage: Math.min(this.data.recordsPage, nextTotalPages)
        });
        await Promise.all([
          this.loadAllRecords(),
          this.loadRecords(),
          this.loadTrend()
        ]);
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
        return values.concat(
          [point.systolic, point.diastolic, point.heart_rate].filter(
            (value) => value !== null && value !== undefined
          )
        );
      }, []);
      const minValue = allValues.length
        ? Math.max(0, Math.floor(Math.min(...allValues) / 20) * 20 - 20)
        : 40;
      const maxValue = allValues.length
        ? Math.ceil(Math.max(...allValues) / 20) * 20 + 20
        : 180;
      const range = Math.max(maxValue - minValue, 1);

      const step = points.length > 1 ? chartWidth / (points.length - 1) : 0;
      const isSingleDayTimeline = (
        this.data.dimension === "day" &&
        this.data.startDate === this.data.endDate
      );
      const getPointX = (point, index) => {
        if (!isSingleDayTimeline) {
          return padding.left + (
            points.length === 1 ? chartWidth / 2 : step * index
          );
        }
        const [hour, minute] = String(point.label).split(":").map(Number);
        const minutes = Math.min(
          Math.max((hour || 0) * 60 + (minute || 0), 0),
          24 * 60
        );
        return padding.left + (minutes / (24 * 60)) * chartWidth;
      };
      const maxLabels = points.length <= 7 ? points.length : 6;
      const labelIndexes = isSingleDayTimeline
        ? []
        : [...new Set(
            Array.from({ length: maxLabels }, (_, index) => (
              Math.round(
                index * (points.length - 1) / Math.max(maxLabels - 1, 1)
              )
            ))
          )];
      const axisTicks = isSingleDayTimeline
        ? Array.from({ length: 12 }, (_, index) => ({
            label: `${pad(index * 2)}:00`,
            x: padding.left + (index * 2 / 24) * chartWidth
          }))
        : labelIndexes.map((index) => ({
            label: points[index].axisLabel || points[index].label,
            x: getPointX(points[index], index)
          }));
      const axisY = padding.top + chartHeight;

      // 网格先绘制，作为折线和数据点的背景。
      ctx.setStrokeStyle("#E5E6EB");
      ctx.setLineWidth(1);
      ctx.setLineDash([4, 4], 0);
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
      axisTicks.forEach(({ x }) => {
        ctx.beginPath();
        ctx.moveTo(x, padding.top);
        ctx.lineTo(x, axisY);
        ctx.stroke();
      });
      ctx.setLineDash([], 0);

      [
        { field: "systolic", color: "#1677FF" },
        { field: "diastolic", color: "#52C41A" },
        { field: "heart_rate", color: "#FA8C16" }
      ].forEach(({ field, color }) => {
        ctx.setStrokeStyle(color);
        ctx.setFillStyle(color);
        ctx.setLineWidth(2);
        let drawing = false;
        points.forEach((point, index) => {
          if (point[field] === null || point[field] === undefined) {
            drawing = false;
            return;
          }
          const x = getPointX(point, index);
          const y = padding.top + (
            (maxValue - point[field]) / range
          ) * chartHeight;
          if (!drawing) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            drawing = true;
          } else {
            ctx.lineTo(x, y);
          }
          const nextPoint = points[index + 1];
          if (
            !nextPoint ||
            nextPoint[field] === null ||
            nextPoint[field] === undefined
          ) {
            ctx.stroke();
            drawing = false;
          }
        });
        points.forEach((point, index) => {
          if (point[field] === null || point[field] === undefined) return;
          const x = getPointX(point, index);
          const y = padding.top + (
            (maxValue - point[field]) / range
          ) * chartHeight;
          ctx.beginPath();
          ctx.arc(x, y, 2.5, 0, Math.PI * 2);
          ctx.fill();
        });
      });

      ctx.setStrokeStyle("#86909C");
      ctx.setLineWidth(1);
      axisTicks.forEach(({ x }) => {
        ctx.beginPath();
        ctx.moveTo(x, axisY);
        ctx.lineTo(x, axisY + 5);
        ctx.stroke();
      });
      ctx.setFillStyle("#86909C");
      ctx.setFontSize(9);
      ctx.setTextAlign("center");
      axisTicks.forEach(({ label, x }) => {
        ctx.save();
        ctx.translate(x, height - 12);
        ctx.rotate(Math.PI / 4);
        ctx.fillText(label, 0, 0);
        ctx.restore();
      });
      ctx.setTextAlign("left");
      ctx.draw();
    }).exec();
  }
});
