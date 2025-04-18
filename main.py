import asyncio
import tomllib
from datetime import datetime
from random import randint

import aiohttp
import re

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase

from loguru import logger

from plugins.GoodMorning.good_morning_db import GoodMorningDB


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

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        main_config = main_config["XYBot"]
        # 获取管理员人员
        self.admins = main_config["managers"]
        
        config = plugin_config["GoodMorning"]

        self.enable = config["enable"]
        self.hello_texts = config["hello_texts"] 
        # 黑名单
        self.blacklist_command_set = config["blacklist_command_set"]
        self.blacklist_command_get = config["blacklist_command_get"]
        self.blacklist_command_delete = config["blacklist_command_delete"]
        # 天气
        self.weather_command_set = config["weather_command_set"]
        self.weather_command_get = config["weather_command_get"]
        self.weather_command_delete = config["weather_command_delete"]
        
        # 初始化db
        self.db = GoodMorningDB()

    # MARK: - 文本消息处理
    @on_text_message()
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        
        # 指令解析
        content = str(message["Content"]).strip()
        content_parts = re.split(r'[\s\u2005]+', content, 1)
        cmd = content_parts[0].strip() if len(content_parts) > 0 else ""
        arg = content_parts[1].strip() if len(content_parts) > 1 else ""

        if cmd in self.blacklist_command_set:
            # 设置黑名单
            await self.blacklist_set(bot, message)
        elif cmd in self.blacklist_command_get:
            # 查询黑名单
            await self.blacklist_get(bot, message)
        elif cmd in self.blacklist_command_delete:
            # 删除黑名单
            await self.blacklist_delete(bot, message)
        elif cmd in self.weather_command_set:
            # 设置天气
            await self.weather_set(bot, message, arg)
        elif cmd in self.weather_command_get:
            # 查询天气
            await self.weather_get(bot, message)
        elif cmd in self.weather_command_delete:
            # 删除天气
            await self.weather_delete(bot, message)
        elif cmd == "获取用户信息":
            # 获取用户信息
            await self.get_user_info(bot, message)
        else:
            return

    async def get_user_info(self, bot: WechatAPIClient, message: dict):
        """获取用户信息"""
        if not await self._check_admin(bot, message):
            return
        logger.info("获取用户信息1111")
        # 获取用户信息
        user_name = await bot.get_user_remark(message["SenderWxid"])
        logger.info(f"user_name -> {user_name}")
        # 获取群信息
        chatroom_name = await bot.get_chatroom_nickname(message["FromWxid"])

        msg = f"用户名: {user_name}\n群聊名: {chatroom_name}"

        logger.info(f"msg -> {msg}")
        await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])


    # MARK: - 黑名单
    async def blacklist_set(self, bot: WechatAPIClient, message: dict):
        # 非群聊不处理
        if not message["IsGroup"]:
            return

        if not await self._check_admin(bot, message):
            return

        logger.info("g-m:admin")
        chatroom_wxid = message["FromWxid"]
        # chatroom_info = await bot.get_chatroom_info(message['FromWxid'])
        # chatroom_nickname = chatroom_info.get("NickName").get("string")
        chatroom_nickname = await bot.get_chatroom_nickname(chatroom_wxid)
        logger.info(f"msg --> {chatroom_nickname}")
        ok = self.db.add_blacklist(chatroom_wxid=chatroom_wxid,chatroom_nickname=chatroom_nickname)
        
        msg = "设置成功" if ok else "设置失败"
        logger.info(f"msg --> {msg}")
        if ok:
            await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])
        else:
            await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])

    async def blacklist_get(self, bot: WechatAPIClient, message: dict):
        if not await self._check_admin(bot, message):
            return
        blacklist_list = self.db.get_blacklist()

        if len(blacklist_list) == 0:
            await bot.send_at_message(message["FromWxid"], "\n黑名单为空", [message["SenderWxid"]])
            return

        reply = [
            f"禁用早晨问候语群列表\n",
            "序号. 群名称",
            "--------------------------------"
        ]
        
        for i, blacklist in enumerate(blacklist_list, 1):
            reply.append(f"{i}. {blacklist.get('chatroom_nickname')}")
            
        msg = "\n".join(reply)
        logger.info(f"msg --> {msg}")

        await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])

    async def blacklist_delete(self, bot: WechatAPIClient, message: dict):
        # 非群聊不处理
        if not message["IsGroup"]:
            return
        if not await self._check_admin(bot, message):
            return

        chatroom_wxid = message["FromWxid"]
        ok = self.db.remove_blacklist(chatroom_wxid=chatroom_wxid)
        msg = "删除成功" if ok else "删除失败"
        if ok:
            await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])

    # MARK: - 天气
    async def weather_set(self, bot: WechatAPIClient, message: dict, city: str):
        # 非群聊不处理
        if not message["IsGroup"]:
            return

        if not await self._check_admin(bot, message):
            return

        if not city:
            await bot.send_at_message(message["FromWxid"], "\n请输入城市", [message["SenderWxid"]])
            return

        chatroom_wxid = message["FromWxid"]
        # chatroom_info = await bot.get_chatroom_info(message['FromWxid'])
        # chatroom_nickname = chatroom_info.get("NickName").get("string")
        chatroom_nickname = await bot.get_chatroom_nickname(chatroom_wxid)
        logger.info(f"msg --> {chatroom_nickname}")

        ok = self.db.add_weather(chatroom_wxid=chatroom_wxid, chatroom_nickname=chatroom_nickname,city=city)
        msg = "设置成功" if ok else "设置失败"
        if ok:
            await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])

    async def weather_get(self, bot: WechatAPIClient, message: dict):
        if not await self._check_admin(bot, message):
            return
        weathers = self.db.get_weather()
        if len(weathers) == 0:
            await bot.send_at_message(message["FromWxid"], "\n天气列表为空", [message["SenderWxid"]])
            return
        reply = [
            f"天气列表\n",
            "序号. 群名称 城市",
        ]

        for i, weather in enumerate(weathers, 1):
            reply.append(f"{i}. {weather.get('chatroom_nickname')} {weather.get('city')}")
        
        msg = "\n".join(reply)

        logger.info(f"msg --> {msg}")
        await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])
        
    async def weather_delete(self, bot: WechatAPIClient, message: dict):
        # 非群聊不处理
        if not message["IsGroup"]:
            return
        if not await self._check_admin(bot, message):
            return

        ok = self.db.remove_weather(chatroom_wxid=message["FromWxid"])
        msg = "删除成功" if ok else "删除失败"
        if ok:
            await bot.send_at_message(message["FromWxid"], "\n" + msg, [message["SenderWxid"]])

    async def _check_admin(self, bot: WechatAPIClient, message: dict) -> bool:
        """检查是否是管理员"""
        sender_wxid = message["SenderWxid"]

        # 非管理员不处理
        if sender_wxid not in self.admins:
            await bot.send_at_message(message["FromWxid"], "\n" + "非管理员不能操作", [message["SenderWxid"]])
            return False

        return True

    # MARK: - 定时任务
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
        
        # chatrooms = ["58405787667@chatroom", "53166638591@chatroom"]

        # 黑名单处理
        blacklist_list = [str(item.get("chatroom_wxid")) for item in self.db.get_blacklist()]
        chatrooms = [x for x in chatrooms if x not in blacklist_list]

        # 天气处理
        weather_list = self.db.get_weather()

        # 提取所有 city 字段
        cities = [item.get("city") for item in weather_list]
        # 添加默认城市
        cities.append("重庆")
        # 去重
        unique_cities = list(set(cities))

        weather_today_map = {}
        # 遍历城市列表
        for city in unique_cities:
            weather_today = await self.get_weather(city)
            weather_today_map[city] = weather_today

        history_today = await self.get_history_today()

        weekend = ["一", "二", "三", "四", "五", "六", "日"]
        message_parts = [
            f"早上好！今天是 {datetime.now().strftime('%Y年%m月%d日')}，星期{weekend[datetime.now().weekday()]}"
        ]
        
        if history_today != "N/A":
            message_parts.extend([
                "",
                "历史上的今天：",
                history_today
            ])

        for chatroom in chatrooms:
            text_parts = message_parts.copy()
            # 天气
            city = "重庆"
            for item in weather_list:
                if item["chatroom_wxid"] == chatroom:
                    city = item["city"]
                    break  # 找到就退出循环
            weather_today = weather_today_map.get(city, "N/A")
            if weather_today!= "N/A":
                text_parts.extend([
                    "",
                    weather_today
                ])
            
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
            # f"风力：{today.get('fengdu', '未知')}\n"
            f"空气质量：{today.get('pm', '未知')}"
        )

    # @schedule('interval', seconds=10)
    async def daily_taskkkk(self, bot: WechatAPIClient):
        current_time = datetime.now().timestamp()
        current_time = int(current_time)

        json = {
            "MsgId": (585326344 + current_time),
            "ToWxid": "wxid_1s8pwoa9rl6f21",
            "FromWxid": "4444@chatroom",
            "IsGroup": True,
            "MsgType": 1,
            "Content": "加入黑名单",
            # "Content": image_data,
            "SenderWxid":"wxid_1s8pwoa9rl6f21",
            "Status": 3,
            "ImgStatus": 1,
            "ImgBuf": {
                "iLen": 0
            },
            "CreateTime": current_time,
            "MsgSource": "<msgsource>\n\t<atuserlist><![CDATA[,wxid_wvp31dkffyml19]]></atuserlist>\n\t<pua>1</pua>\n\t<silence>0</silence>\n\t<membercount>3</membercount>\n\t<signature>V1_cqxXBat9|v1_cqxXBat9</signature>\n\t<tmp_node>\n\t\t<publisher-id></publisher-id>\n\t</tmp_node>\n</msgsource>\n",
            "PushContent": "xxx在群聊中@了你",
            "NewMsgId": 324944634,
            "MsgSeq": 773900177,
            "Quote": {  # 被引用的原始消息信息
                "MsgType": 3,  # 原始消息类型（1表示文本消息）
                "NewMsgId": "324944634",  # 原始消息的ID
                "ToWxid": "wxid_00000000000000",  # 原始消息接收者ID
                "FromWxid": "wxid_11111111111111",  # 原始消息发送者ID
                "Nickname": "XYBot",  # 原始消息发送者昵称
                "MsgSource": "<msgsource>...</msgsource>",  # 原始消息源数据
                "Content": f"引用的消息内容 {current_time}",  # 引用的消息内容
                "Createtime": "1739879158"  # 原始消息创建时间
            }
        }


        try:
            await self.handle_text(bot, json)

        except Exception as e:
            logger.error(f"Error: {e}")