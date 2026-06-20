function toValidNumber(value, min, max) {
  if (value === null || value === undefined || value === "") return "";
  const number = Number(value);
  if (!Number.isFinite(number) || number < min || number > max) return "";
  return String(Math.round(number));
}

function normalizeOcrResult(response) {
  const result = response && response.data && typeof response.data === "object"
    ? response.data
    : (response || {});

  const systolic = toValidNumber(result.systolic, 50, 260);
  const diastolic = toValidNumber(result.diastolic, 30, 180);
  const heartRate = toValidNumber(
    result.heart_rate !== undefined ? result.heart_rate : result.heartRate,
    30,
    220
  );

  return {
    systolic,
    diastolic,
    heartRate,
    complete: Boolean(systolic && diastolic && Number(systolic) > Number(diastolic)),
    hasAnyValue: Boolean(systolic || diastolic || heartRate),
    notice: result.notice || "",
    rawText: Array.isArray(result.raw_text) ? result.raw_text : []
  };
}

module.exports = {
  normalizeOcrResult
};
