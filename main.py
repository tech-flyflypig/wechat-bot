from flask import Flask, request
import xml.etree.ElementTree as ET
from WXBizMsgCrypt3 import WXBizMsgCrypt
import requests
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# 企业微信配置   请替换为实际的企业微信配置
CORP_ID = ""            #- 企业ID（CORP_ID）
TOKEN = ""              #- 应用ID（AGENT_ID）
ENCODING_AES_KEY = ""   #- 消息加解密密钥（ENCODING_AES_KEY）
AGENT_ID = "1000002"    #- 应用ID（AGENT_ID）
CORPSECRET = ""         #- 应用Secret（CORPSECRET）

# DeepSeek API配置
DEEPSEEK_API_KEY = ""   #- 替换为实际的DeepSeek API Key
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"   #- 替换为实际的DeepSeek API地址

# 初始化加解密类
wxcpt = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)

logger = logging.getLogger(__name__)

# 添加一个简单的消息ID缓存
processed_msgs = set()

def call_deepseek_api(message):
    """调用DeepSeek API"""
    logger.info(f"开始调用 DeepSeek API，消息内容: {message}")
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-r1-distill-llama-70b",
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        reply = result['choices'][0]['message']['content']
        logger.info(f"DeepSeek API 返回结果: {reply}")
        return reply
    except Exception as e:
        logger.error(f"DeepSeek API调用错误: {str(e)}")
        return "抱歉,我现在无法回答您的问题。"

def get_access_token():
    """获取企业微信 access_token"""
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORPSECRET}"
    try:
        response = requests.get(url).json()
        logger.info(f"获取access_token响应: {response}")
        if response.get("errcode") != 0:
            logger.error(f"获取access_token失败: {response}")
            return None
        return response.get("access_token")
    except Exception as e:
        logger.error(f"获取access_token异常: {e}")
        return None

def send_work_weixin_message(message: dict):
    """发送企业微信应用消息"""
    logger.info(f"准备发送消息: {message}")
    access_token = get_access_token()
    if not access_token:
        logger.error("获取access_token失败")
        return
        
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    try:
        response = requests.post(url, json=message)
        result = response.json()
        logger.info(f"发送消息响应: {result}")
        if result["errcode"] != 0:
            logger.error(f"发送消息失败: {result}")
    except Exception as e:
        logger.error(f"发送消息异常: {e}")

def split_message(message: str, max_bytes: int = 2040) -> list:
    """将消息分段，每段不超过指定字节数"""
    messages = []
    start_pos = 0
    total_length = len(message)
    
    while start_pos < total_length:
        # 二分查找确定最大可能的字符数
        left, right = 1, total_length - start_pos
        while left < right:
            mid = (left + right + 1) // 2
            if len(message[start_pos:start_pos + mid].encode('utf-8')) <= max_bytes:
                left = mid
            else:
                right = mid - 1
        
        # 添加当前段落
        messages.append(message[start_pos:start_pos + left])
        
        # 更新起始位置
        start_pos += left
    
    return messages

def process_message(msg: dict):
    """处理消息的具体逻辑"""
    try:
        # 调用 DeepSeek API 获取回复
        response = call_deepseek_api(msg["Content"])
        # 去掉开头的换行符
        response = response.lstrip('\n')
        logger.info(f"获取到AI回复: {response}")
        
        # 将回复分段
        response_parts = split_message(response)
        logger.info(f"回复被分为 {len(response_parts)} 段")
        
        # 同步发送所有消息，确保顺序
        for i, part in enumerate(response_parts, 1):
            # 如果消息被分段，添加标记
            if len(response_parts) > 1:
                prefix = f"[{i}/{len(response_parts)}] "
                # 确保添加标记后总长度不超过限制
                available_length = 2040 - len(prefix.encode('utf-8'))
                while len((prefix + part).encode('utf-8')) > 2040:
                    part = part[:-1]
                part = prefix + part.lstrip('\n')
                
            # 同步发送消息
            send_work_weixin_message({
                "touser": msg["FromUserName"],
                "msgtype": "text",
                "agentid": AGENT_ID,
                "text": {
                    "content": part
                }
            })
            
            # 添加短暂延迟确保消息顺序
            time.sleep(0.5)
                
    except Exception as e:
        logger.error(f"处理消息失败: {e}")

def parse_xml(xml_string):
    """解析XML消息"""
    try:
        xml_tree = ET.fromstring(xml_string)
        msg_type = xml_tree.find("MsgType").text
        from_username = xml_tree.find("FromUserName").text
        content = xml_tree.find("Content").text if msg_type == "text" else ""
        msg_id = xml_tree.find("MsgId").text if xml_tree.find("MsgId") is not None else None
        return msg_type, from_username, content, msg_id
    except Exception as e:
        logger.error(f"XML解析错误: {str(e)}")
        return None, None, None, None

@app.route('/wxcallback', methods=['GET', 'POST'])
def wx_callback():
    # 获取URL参数
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    
    # 处理URL验证请求
    if request.method == 'GET':
        echostr = request.args.get('echostr')
        print(f"收到验证请求: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")
        
        ret, echo_str = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
        print(f"验证结果: ret={ret}, echo_str={echo_str}")
        
        if ret == 0:
            return echo_str
        return f"验证失败，错误码: {ret}"

    # 处理POST请求（接收消息）
    try:
        # 获取加密消息
        req_data = request.data
        if not req_data:
            return "success"
            
        req_data = req_data.decode('utf-8')
        logger.info(f"收到消息: {req_data}")
        
        # 解密消息
        ret, xml_content = wxcpt.DecryptMsg(req_data, msg_signature, timestamp, nonce)
        if ret != 0:
            logger.error(f"消息解密失败，错误码: {ret}")
            return "success"
            
        # 解析消息内容
        msg_type, from_username, content, msg_id = parse_xml(xml_content)
        if not all([msg_type, from_username]):
            return "success"
            
        # 只处理文本消息
        if msg_type == "text":
            # 检查消息是否已处理
            if msg_id and msg_id in processed_msgs:
                logger.info(f"消息 {msg_id} 已处理，跳过")
                return "success"
            
            # 添加到已处理集合
            if msg_id:
                processed_msgs.add(msg_id)
                if len(processed_msgs) > 1000:
                    processed_msgs.clear()
            
            # 立即发送"思考中..."消息
            send_work_weixin_message({
                "touser": from_username,
                "msgtype": "text",
                "agentid": AGENT_ID,
                "text": {
                    "content": "思考中..."
                }
            })
            
            # 使用线程池处理消息，但每个消息只处理一次
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(process_message, {
                "MsgType": msg_type,
                "FromUserName": from_username,
                "Content": content,
                "MsgId": msg_id
            })
            executor.shutdown(wait=False)  # 不等待执行完成就关闭线程池
            
            return "success"
        
        return "success"
        
    except Exception as e:
        logger.error(f"处理消息时发生错误: {str(e)}")
        return "success"

# 添加日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8889, debug=True)
