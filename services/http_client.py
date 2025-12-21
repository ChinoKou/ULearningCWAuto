import asyncio
from traceback import format_exc

import httpx
from loguru import logger


class HttpClient:
    """内部Http客户端"""

    def __init__(
        self, token: str = "abc", cookies: dict | None = None, debug: bool = False
    ) -> None:
        """
        内部Http客户端初始化

        :param token: 鉴权令牌
        :type token: str
        :param cookies: Cookie字典对象
        :type cookies: dict | None
        :param debug: 是否为调试模式
        :type debug: bool
        """

        self.debug = debug
        self.__client = httpx.AsyncClient(verify=not self.debug)
        USER_AGENT = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
        )
        headers = {"User-Agent": USER_AGENT}
        if token != "abc":
            headers["Authorization"] = token

        self.__client.headers.update(headers)
        if cookies:
            self.__client.cookies.update(cookies)

    async def get(
        self,
        url: str,
        params: dict | None = None,
        timeout: int = 8,
        retry: int = 0,
        follow_redirects: bool = False,
    ) -> httpx.Response | None:
        """
        发送GET请求

        :param url: 请求的URL
        :type url: str
        :param params: 请求头的Params
        :type params: dict | None
        :param timeout: 请求超时时间
        :type timeout: int
        :param retry: 递归调用重试次数
        :type retry: int
        :param follow_redirects: 是否跟随重定向
        :type follow_redirects: bool
        :return: 响应体
        :rtype: Response | None
        """
        url_log = url
        if "isValidToken" in url:
            token = url.split("/").pop()
            url_log = url.replace(token, "*" * len(token))
        logger.debug(f"[HTTP][GET] {url_log}")

        try:
            return await self.__client.get(
                url, params=params, timeout=timeout, follow_redirects=follow_redirects
            )

        except httpx.TransportError as e:
            logger.error(f"[HTTP][GET] 网络错误: {e}")
            if retry >= 3:
                logger.error("[HTTP][GET] 请求重试次数过多")
                return None

            await asyncio.sleep(0.5)
            logger.info(f"[HTTP][GET] 正在重试 {url_log}")
            return await self.get(url, params=params, timeout=timeout, retry=retry + 1)

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP][GET] 请求出错: {e}")
            return None

    async def post(
        self,
        url: str,
        content: str | None = None,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
        timeout: int = 8,
        retry: int = 0,
        follow_redirects: bool = False,
    ) -> httpx.Response | None:
        """
        发送POST请求

        :param url: 请求的URL
        :type url: str
        :param content: 请求体的内容
        :type content: str | None
        :param params: 请求头的Params
        :type params: dict | None
        :param json: 请求体的JSON数据
        :type json: dict | None
        :param data: 请求体的urlencoded数据
        :type data: dict | None
        :param timeout: 请求超时时间
        :type timeout: int
        :param retry: 递归调用重试次数
        :type retry: int
        :param follow_redirects: 是否跟随重定向
        :type follow_redirects: bool
        :return: 响应体
        :rtype: Response | None
        """
        logger.debug(f"[HTTP][POST] {url}")

        try:
            return await self.__client.post(
                url=url,
                content=content,
                params=params,
                json=json,
                data=data,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )

        except httpx.TransportError as e:
            logger.error(f"[HTTP][POST] 网络错误: {e}")
            if retry >= 3:
                logger.error("[HTTP][POST] 请求重试次数过多")
                return None

            await asyncio.sleep(0.5)
            logger.info(f"[HTTP][POST] 正在重试 {url}")
            return await self.post(
                url=url,
                content=content,
                params=params,
                json=json,
                data=data,
                timeout=timeout,
                retry=retry + 1,
            )

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP][POST] 请求出错: {e}")
            return None

    def set_token(self, token: str) -> bool:
        """
        设置token

        :param token: 鉴权令牌
        :type token: str
        :return: 是否设置成功
        :rtype: bool

        """
        logger.debug(f"[HTTP] 设置token")

        try:
            # 更新客户端请求头的Authorization属性
            self.__client.headers.update({"Authorization": token})
            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP] 设置token出错: {e}")
            return False

    def set_cookies(self, cookies: dict) -> bool:
        """
        设置cookies

        :param cookies: Cookies字典对象
        :type cookies: dict
        :return: 是否设置成功
        :rtype: bool

        """
        logger.debug("[HTTP] 设置cookies")

        try:
            # 更新客户端的Cookie
            self.__client.cookies.update(cookies)
            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP] 设置cookies出错: {e}")
            return False

    def get_cookies(self) -> dict:
        """
        获取cookies

        :return: Cookies字典对象
        :rtype: dict[Any, Any]

        """
        logger.debug("[HTTP] 获取cookies")

        try:
            # 获取内部客户端的Cookie
            cookies = {}
            for cookie in self.__client.cookies.jar:
                if cookie.name not in cookies:
                    cookies[cookie.name] = cookie.value

            return cookies

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP] 获取cookies出错: {e}")
            return {}

    def copy_client(self) -> "HttpClient | None":
        """
        复制Http客户端

        :return: HttpClient对象
        :rtype: HttpClient | None
        """
        logger.debug("[HTTP] 复制Http客户端")

        try:
            # 获取当前鉴权令牌
            token = self.__client.headers.get("Authorization")

            # 创建新的HttpClient
            new_http_client = HttpClient(
                token=token, cookies=self.get_cookies(), debug=self.debug
            )
            return new_http_client

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP] 复制Http客户端出错: {e}")
            return None

    async def re_create_client(
        self, token: str = "abc", cookies: dict | None = None, debug: bool = False
    ) -> bool:
        """
        重新创建内部Http客户端

        :param token: 鉴权令牌
        :type token: str
        :param cookies: Cookies字典对象
        :type cookies: dict | None
        :param debug: 是否为调试模式
        :type debug: bool
        :return: 是否重新创建成功
        :rtype: bool

        """
        logger.debug("[HTTP] 重新创建内部Http客户端")

        try:
            # 创建新的内部客户端AsyncClient
            new_client = httpx.AsyncClient(verify=not debug)

            # 初始化请求头和Cookie
            if token != "abc":
                self.__client.headers.update({"Authorization": token})

            new_client.headers.update(self.__client.headers)
            new_client.cookies.update(self.__client.cookies)

            if cookies:
                new_client.cookies.update(cookies)

            # 关闭旧的内部客户端并替换为新的内部客户端
            await self.__client.aclose()
            self.__client = new_client

            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[HTTP] 重新创建内部Http客户端出错: {e}")
            return False
