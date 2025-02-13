# 企业微信智能机器人

基于企业微信API和DeepSeek大模型API开发的智能对话机器人，支持自动响应企业微信消息。


## 功能特点

- 🤖 集成DeepSeek大语言模型，提供智能对话能力
- 🌐 兼容OpenAI API协议，支持各类大语言模型
- 💬 支持企业微信消息的自动回复
- 🔒 完整的消息加密解密机制
- 🚀 异步处理消息，提高响应效率
- 📝 智能分段回复，支持长文本消息
- 📊 完整的日志记录功能

## 安装部署

### 环境要求

- Python 3.7+
- 企业微信管理员权限
- DeepSeek API 密钥

### 安装步骤

1. 克隆代码
```bash
git clone https://github.com/tech-flyflypig/wechat-bot.git
cd wechat-bot
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# Windows使用：
# venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置应用变量
```
main.py：
CORP_ID=你的企业ID
AGENT_ID=应用ID
TOKEN=Token
ENCODING_AES_KEY=消息加密密钥
CORPSECRET=应用Secret
DEEPSEEK_API_KEY=DeepSeek API密钥
DEEPSEEK_API_URL=DeepSeek API地址
```

### 部署运行

1. 开发环境运行
```bash
python main.py
```

2. 生产环境部署（使用gunicorn）
```bash
gunicorn -w 4 -b 0.0.0.0:8889 main:app \
--timeout 120 \
--workers 4 \
--threads 2 \
--worker-class=gthread \
main:app
```
3. 使用systemd服务部署
```bash
# 复制服务文件
sudo cp wechat-bot.service /etc/systemd/system/

# 修改服务文件中的路径
sudo vim /etc/systemd/system/wechat-bot.service
# 需要修改:
# WorkingDirectory=/path/to/wechat-bot
# ExecStart=/path/to/python /path/to/wechat-bot/main.py

# 重载服务
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start wechat-bot

# 设置开机自启
sudo systemctl enable wechat-bot

# 查看服务状态
sudo systemctl status wechat-bot
```

## 配置说明

### 企业微信配置

1. 登录[企业微信管理后台](https://work.weixin.qq.com/wework_admin/frame)
2. 创建自建应用，获取以下信息：
   - 企业ID（CORP_ID）
   - 应用ID（AGENT_ID）
   - 应用Secret（CORPSECRET）
3. 在应用设置页面配置：
   - 接收消息服务器配置
   - 生成Token和EncodingAESKey

### DeepSeek配置

1. 获取DeepSeek API密钥
2. 配置到环境变量DEEPSEEK_API_KEY中

## 使用说明

1. 在企业微信中找到已配置的应用
2. 发送消息即可开始对话
3. 机器人会自动应答，支持智能对话

## 注意事项

- 请妥善保管各类密钥和敏感信息
- 建议在生产环境使用HTTPS
- 注意控制API调用频率，避免超出限制
- 定期检查并更新依赖包版本

## 开源协议

MIT License