/**
 * 生产环境默认使用 hiothy.cn。
 * 本地调试可改为 http://127.0.0.1:5000/api/v1，
 * 真机调试需使用电脑局域网 IP，不能使用 127.0.0.1。
 */
// 正式上线域名配置
// const BASE_URL = "https://hiothy.cn/api/v1";
// 测试正式ip
const BASE_URL = "http://127.0.0.1:5000/api/v1";

module.exports = {
  BASE_URL,
  REQUEST_TIMEOUT: 30000,
  UPLOAD_TIMEOUT: 120000
};
