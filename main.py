import asyncio
import tomllib
from datetime import datetime
from random import randint

import aiohttp

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

from loguru import logger


class GoodMorning(PluginBase):
    description = "早上好插件"
    author = "HenryXiaoYang"
    version = "1.0.1"

    # Change Log
    # 1.0.1 fix ssl issue, add timeout

    def __init__(self):
        super().__init__()

        with open("plugins/GoodMorning/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["GoodMorning"]

        self.enable = config["enable"]
        self.hello_texts = config["hello_texts"]        # self.active_days = config.get("active_days", [1,2,3,4,5])  # 默认工作日发

    @schedule('cron', day_of_week='mon-fri', hour=7, minute=0)
    async def daily_task(self, bot: WechatAPIClient):
        if not self.enable:
            return

        id_list = []
        wx_seq, chatroom_seq = 0, 0
        while True:
            contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
            id_list.extend(contact_list["ContactUsernameList"])
            wx_seq = contact_list["CurrentWxcontactSeq"]
            chatroom_seq = contact_list["CurrentChatRoomContactSeq"]
            if contact_list["CountinueFlag"] != 1:
                break

        chatrooms = []
        for id in id_list:
            if id.endswith("@chatroom"):
                chatrooms.append(id)

        
        history_today = await self.get_history_today()
        weather_today = await self.get_weather("重庆")

        weekend = ["一", "二", "三", "四", "五", "六", "日"]
        message_parts = [
            f"早上好！今天是 {datetime.now().strftime('%Y年%m月%d号')}，星期{weekend[datetime.now().weekday()]}"
        ]
        
        if history_today != "N/A":
            message_parts.extend([
                "",
                "历史上的今天：",
                history_today
            ])
            
        if weather_today != "N/A":
            message_parts.extend([
                "",
                weather_today
            ])

        # message_parts.extend([
        #     "",
        #     "腾邦嗵达物流在线接单！"
        #     "祝各位老板生意兴隆"
        # ])
            
        # message = "\n".join(message_parts)
        # logger.info(f"message --> {message}")
        
        for chatroom in chatrooms:
            text_parts = message_parts.copy()
            # 获取随机问候语
            random_hello_text = self._random_hello_text()
            # 插入换行
            random_hello_text.insert(0, "")
            # 添加到列表中
            text_parts.extend(random_hello_text)
            message = "\n".join(text_parts)

            logger.info(f"message --> {message}")

            await bot.send_text_message(chatroom, message)
            await asyncio.sleep(randint(1, 5))

    def _random_hello_text(self):
        """随机获取问候语"""
        return self.hello_texts[randint(0, len(self.hello_texts) - 1)].copy()

    async def get_history_today(self, limit_num: int = 3):
        """获取历史上的今天数据"""
        try:
            async with aiohttp.request("GET", "https://v2.api-m.com/api/history", ssl=False) as req:
                resp = await req.json()
                history_today = "N/A"
                if resp.get("data"):
                    history_events = resp.get("data", [])[:limit_num]  # 只取前3条数据
                    history_today = "\n".join([str(event) for event in history_events])
                return history_today
        except Exception as e:
            logger.error(f"获取历史上的今天异常: {e}")
            return "N/A"

    async def get_weather(self, city):
        """获取指定城市的天气数据"""
        try:
            url = f"https://v.api.aa1.cn/api/api-tianqi-3/index.php?msg={city}&type=1"
            async with aiohttp.request("GET", url, ssl=False) as req:
                resp = await req.text()
                
                # 提取并解析JSON数据
                json_data = self._extract_weather_json(resp)
                if not json_data:
                    return "N/A"
                
                # 获取今天的天气数据
                today_weather = self._get_today_weather(json_data, city)
                return today_weather
                
        except Exception as e:
            logger.error(f"获取天气异常: {e}")
            return "N/A"
    
    def _extract_weather_json(self, response_text):
        """从响应文本中提取JSON数据"""
        import re
        import json
        
        # 尝试从响应中提取JSON数据
        json_pattern = re.compile(r'(\{\s*"code"\s*:\s*"1"[\s\S]*\})')
        match = json_pattern.search(response_text)
        
        if not match:
            logger.error("未找到天气JSON数据")
            return None
            
        json_str = match.group(1)
        logger.debug(f"提取的JSON数据长度: {len(json_str)}")
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return None
    
    def _get_today_weather(self, weather_data, city):
        """从天气数据中获取今天的天气信息"""
        if not weather_data or weather_data.get("code") != "1" or not weather_data.get("data"):
            return "N/A"
            
        # 获取当前星期几
        current_weekday = datetime.now().weekday()  # 0-6 对应周一到周日
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        current_weekday_name = weekday_names[current_weekday]
        
        # 查找匹配当前星期的天气数据
        today = None
        for day_data in weather_data["data"]:
            if day_data.get("riqi") == current_weekday_name:
                today = day_data
                break
        
        if not today:
            return "N/A"
            
        # 格式化天气信息
        return (
            f"{city}今日天气：\n"
            f"温度：{today.get('wendu', '未知')}\n"
            f"天气：{today.get('tianqi', '未知')}\n"
            f"风力：{today.get('fengdu', '未知')}\n"
            f"空气质量：{today.get('pm', '未知')}"
        )
