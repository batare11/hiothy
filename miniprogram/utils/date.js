function pad(value) {
  return String(value).padStart(2, "0");
}

function formatDate(date) {
  const value = date instanceof Date ? date : new Date(date);
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  return `${formatDate(date)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function oneYearAgo() {
  const date = new Date();
  date.setFullYear(date.getFullYear() - 1);
  return formatDate(date);
}

module.exports = {
  formatDate,
  formatDateTime,
  oneYearAgo
};

