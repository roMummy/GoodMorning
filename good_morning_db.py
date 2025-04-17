from database.XYBotDB import *
from datetime import datetime
from sqlalchemy import delete

class GoodMorningBlacklist(Base):
    """
    黑名单表
    id: 主键
    chatroom_wxid: 群聊wxid
    chatroom_nickname: 群聊昵称
    update_time: 更新时间
    """
    __tablename__ = 'good_morning_blacklist'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chatroom_wxid = Column(String(40), index=True, comment='群聊wxid')
    chatroom_nickname = Column(String(255), index=True, comment='群聊昵称')
    update_time = Column(DateTime, default=datetime.now, index=True, comment='更新时间')


class GoodMorningWeather(Base):
    """
    天气表
    id: 主键
    city: 城市
    chatroom_wxid: 群聊wxid
    chatroom_nickname: 群聊昵称
    update_time: 更新时间
    """
    __tablename__ = 'good_morning_weather'
    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(40), index=True, comment='城市')
    chatroom_wxid = Column(String(40), index=True, comment='群聊wxid')
    chatroom_nickname = Column(String(255), index=True, comment='群聊昵称')
    update_time = Column(DateTime, default=datetime.now().timestamp, index=True, comment='更新时间')

class GoodMorningDB(XYBotDB):
    def __init__(self):
        super().__init__()
    
    # MARK: - 黑名单
    def add_blacklist(self, chatroom_wxid: str, chatroom_nickname: str):
        """
        添加黑名单
        :param chatroom_wxid: 群聊wxid
        :param chatroom_nickname: 群聊昵称
        :return:
        """
        return self._execute_in_queue(self._add_blacklist, chatroom_wxid, chatroom_nickname)

    def _add_blacklist(self, chatroom_wxid: str, chatroom_nickname: str):
        session = self.DBSession()

        try:
            result = session.execute(
                update(GoodMorningBlacklist)
                .where(GoodMorningBlacklist.chatroom_wxid == chatroom_wxid)
                .values(
                    chatroom_nickname=chatroom_nickname,
                    update_time=datetime.now()
                )
            )
            if result.rowcount == 0:
                session.add(GoodMorningBlacklist(
                    chatroom_wxid=chatroom_wxid,
                    chatroom_nickname=chatroom_nickname,
                    update_time=datetime.now()
                ))

            logger.info(f"添加黑名单成功: {chatroom_wxid} {chatroom_nickname}")
            session.commit()
            return True
        except Exception as e:
            logger.error(f"添加黑名单失败: {chatroom_wxid} {chatroom_nickname} {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def remove_blacklist(self, chatroom_wxid: str):
        """
        删除黑名单
        :param chatroom_wxid: 群聊wxid
        """

        session = self.DBSession()
        try:
            session.execute(
                delete(GoodMorningBlacklist)
                .where(GoodMorningBlacklist.chatroom_wxid == chatroom_wxid)
            )
            session.commit()
            logger.info(f"删除黑名单成功: {chatroom_wxid}")
            return True
        except Exception as e:
            logger.error(f"删除黑名单失败: {chatroom_wxid} {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_blacklist(self) -> [dict]:
        """
        获取黑名单
        """
        session = self.DBSession()
        try:
            result = session.query(GoodMorningBlacklist).order_by(GoodMorningBlacklist.update_time.desc()).all()
            logger.info(f"获取黑名单成功: {result}")
            return [{
                "chatroom_wxid": item.chatroom_wxid,
                "chatroom_nickname": item.chatroom_nickname,
                "update_time": item.update_time
            } for item in result]
        except Exception as e:
            logger.error(f"获取黑名单失败: {e}")
            return []
        finally:
            session.close()

    # MARK: - 天气
    def add_weather(self, city: str, chatroom_wxid: str, chatroom_nickname: str):
        """
        添加天气
        :param city: 城市
        :param chatroom_wxid: 群聊wxid
        :param chatroom_nickname: 群聊昵称
        """
        return self._execute_in_queue(self._add_weather, city, chatroom_wxid, chatroom_nickname)
    
    def _add_weather(self, city: str, chatroom_wxid: str, chatroom_nickname: str):
        session = self.DBSession()
        try:
            result = session.execute(
                update(GoodMorningWeather)
               .where(GoodMorningWeather.chatroom_wxid == chatroom_wxid)
               .values(
                    city=city,
                    chatroom_nickname=chatroom_nickname,
                    update_time=datetime.now()
                )
            )
            if result.rowcount == 0:
                session.add(GoodMorningWeather(
                    city=city,
                    chatroom_wxid=chatroom_wxid,
                    chatroom_nickname=chatroom_nickname,
                    update_time=datetime.now()
                ))
            
            logger.info(f"添加天气成功: {city} {chatroom_wxid} {chatroom_nickname}")
            session.commit()
            return True
        except Exception as e:
            logger.error(f"添加天气失败: {city} {chatroom_wxid} {chatroom_nickname} {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def remove_weather(self, chatroom_wxid: str):
        """
        删除天气
        :param chatroom_wxid: 群聊wxid
        """
        session = self.DBSession()
        try:
            session.execute(
                delete(GoodMorningWeather)
               .where(GoodMorningWeather.chatroom_wxid == chatroom_wxid)        
            )
            session.commit()
            logger.info(f"删除天气成功: {chatroom_wxid}")
            return True
        except Exception as e:
            logger.error(f"删除天气失败: {chatroom_wxid} {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_weather(self) -> [dict]:
        """
        获取天气
        """
        session = self.DBSession()
        try:
            result = session.query(GoodMorningWeather).order_by(GoodMorningWeather.update_time.desc()).all()
            logger.info(f"获取天气成功: {result}")
            return [{
                "city": item.city,
                "chatroom_wxid": item.chatroom_wxid,
                "chatroom_nickname": item.chatroom_nickname,
                "update_time": item.update_time 
            } for item in result]

        except Exception as e:
            logger.error(f"获取天气失败: {e}")
            return []
        finally:
            session.close()