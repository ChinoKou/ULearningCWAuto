import json
from traceback import format_exc
from typing import TYPE_CHECKING
from urllib.parse import unquote

from loguru import logger

from models import APIUrl, LoginAPIUserInfoResponse, UserConfig

if TYPE_CHECKING:
    from config import Config
    from services import HttpClient


class LoginAPI:
    """登录 API"""

    def __init__(self, username: str, config: "Config", client: "HttpClient") -> None:
        """
        登录 API初始化

        :param username: 要登录的用户名
        :type username: str
        :param config: 配置对象
        :type config: "Config"
        :param client: 内部Http客户端对象
        :type client: "HttpClient"
        """

        self.user_config: UserConfig = config.users[username]
        self.config: Config = config
        self.client: "HttpClient" = client
        self.api: APIUrl = APIUrl.create(self.user_config.site)

    async def login(self) -> LoginAPIUserInfoResponse | None:
        """
        执行登录并用户信息API

        :return: 登录获取的用户信息API响应模型
        :rtype: LoginAPIUserInfoResponse | None
        """
        logger.debug("[API][O] 执行登录并获取用户信息")

        try:
            # 构造 url 与请求体
            url = f"{self.api.course_api}/users/login/v2"
            payload = {
                "loginName": self.user_config.username,
                "password": self.user_config.password,
            }

            resp = await self.client.post(url=url, data=payload)

            if not resp or resp.status_code != 302:
                status_code = resp.status_code if resp else None
                logger.error(f"[API] 执行登录并用户信息时网络出错: HTTP {status_code}")
                return None

            # 解析数据
            USERINFO = resp.cookies.get("USERINFO", "")

            if not USERINFO:
                return None

            # URL 解码
            user_info = json.loads(unquote(USERINFO))

            # 转换为模型
            resp_model = LoginAPIUserInfoResponse.parse(user_info)

            logger.debug(f"[API][✓] 执行登录并获取用户信息")

            return resp_model

        except Exception as e:
            logger.error(f"{format_exc()}\n[API] 执行登录并用户信息时发生错误: {e}")
            return None

    async def check_login_status(self) -> bool:
        """
        检查Token是否有效

        :return: Token有效状态
        :rtype: bool
        """
        logger.debug("[API][O] 检查Token是否有效")

        try:
            # 构造 url 与请求体
            url = f"{self.api.course_api}/users/isValidToken/{self.user_config.token}"

            resp = await self.client.get(url)

            if not resp or resp.status_code != 200:
                status_code = resp.status_code if resp else None
                logger.error(f"[API] 检查 Token 是否有效时网络出错: HTTP {status_code}")
                raise

            # 检查接口返回值
            parse_info = resp.text.strip().lower() == "true"

            logger.debug(f"[API][✓] 检查Token是否有效")

            return parse_info

        except Exception as e:
            logger.error(f"{format_exc()}\n[API] 检查Token是否有效时发生错误: {e}")
            return False
