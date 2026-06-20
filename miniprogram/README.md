# 原生微信小程序

## 导入运行

1. 打开微信开发者工具，选择“导入项目”。
2. 项目目录选择本目录 `miniprogram/`。
3. 开发阶段可使用测试号；发布前将 `project.config.json` 中的 `appid` 改为正式小程序 AppID。
4. 修改 `config/index.js` 中的 `BASE_URL`：

```js
// 开发版、体验版和正式版
const BASE_URL = "https://hiothy.cn/api/v1";
```

5. 本机调试时，在微信开发者工具“详情 → 本地设置”中勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。

## 页面

- 首页：拍照/相册 OCR、人工修正、手工录入、趋势图、最近记录。
- 消息中心：最新未读消息、已读消息、查看后自动标记已读。
- 个人中心：头像、昵称、性别、出生日期、手机号、意见反馈。

## 生产环境说明

- 在微信公众平台添加 `https://hiothy.cn` 为 `request` 和 `uploadFile` 合法域名。
- 开发版、体验版和正式版均通过 `wx.login` 获取真实微信身份。后端 AppID 必须与 `project.config.json` 一致。
- AppSecret 只配置在服务器 `.env`，不要写入小程序代码。
- `chooseAvatar` 返回的是临时文件路径；生产版应增加头像上传接口，将图片存储到对象存储后再保存永久 URL。
