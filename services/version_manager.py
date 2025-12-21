from traceback import format_exc
from typing import TYPE_CHECKING

import questionary
from loguru import logger

from .http_client import HttpClient
from utils import answer

if TYPE_CHECKING:
    from httpx import Response


class VersionManager:
    """版本管理类"""

    def __init__(self) -> None:
        """版本管理类初始化"""
        self.tag = "v1.1.5"  # 硬编码
        self.client = HttpClient()

    async def get_latest_info(
        self, use_proxy: bool = True
    ) -> tuple[str | None, str | None] | None:
        """
        获取最新版本信息

        :param use_proxy: 是否使用代理
        :type use_proxy: bool
        :return: 最新版本号和发布信息
        :rtype: tuple[str | None, str | None] | None
        """
        logger.debug("[MANAGER][VERSION][O] 获取最新版本号")

        try:

            async def request(url) -> "Response | None":
                """
                获取版本信息

                :param url: 请求URL
                :return: 响应对象
                :rtype: Response | None
                """
                resp = await self.client.get(url=url, timeout=3, follow_redirects=True)
                if not resp or resp.status_code != 200:
                    status_code = resp.status_code if resp else None
                    logger.error(
                        f"[MANAGER][VERSION] 获取最新版本号时网络出错: HTTP {status_code}"
                    )
                    return None

                return resp

            # 构造 url
            url = "https://api.github.com/repos/ChinoKou/UCourseAuto/releases/latest"
            proxy_urls = [
                "https://gh-proxy.org/",
                "https://hk.gh-proxy.org/",
                "https://cdn.gh-proxy.org/",
                "https://edgeone.gh-proxy.org/",
            ]

            resp: "Response | None" = None

            # 使用代理
            if use_proxy:

                # 检测 Github 代理
                for proxy in proxy_urls:
                    logger.debug(f"[MANAGER][VERSION] 正在检测 Github 代理: {proxy}")
                    resp = await self.client.get(url=proxy, timeout=1, retry=2)

                    # 代理可用
                    if resp and resp.status_code < 500:
                        logger.debug(f"[MANAGER][VERSION] 使用 Github 代理: {proxy}")

                        # 构造请求 URL
                        proxy_url = proxy + url
                        resp = await request(url=proxy_url)
                        if resp:
                            break

                        # 请求失败, 尝试下一个代理
                        logger.debug(
                            f"[MANAGER][VERSION] 使用 Github 代理: {proxy} 出错, 尝试下一个代理"
                        )

                    # 代理不可用
                    else:
                        logger.debug(
                            f"[MANAGER][VERSION] Github 代理: {proxy} 不可用, 尝试下一个代理"
                        )

                # 所有代理均不可用
                if not resp:
                    logger.warning("所有 Github 代理均不可用, 尝试直接访问")
                    return await self.get_latest_info(use_proxy=False)

            # 不使用代理
            else:
                resp = await request(url=url)

            # 获取失败
            if not resp:
                return None

            # 解析数据
            resp_body: dict = resp.json()
            release_tag: str | None = resp_body.get("tag_name")
            release_content: str | None = resp_body.get("body")

            logger.debug(f"[MANAGER][VERSION][✓] 获取最新版本号")

            return release_tag, release_content

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][VERSION] 获取最新版本号时出错: {e}"
            )
            return None

    async def check_version(self) -> bool:
        """
        检查版本是否为最新

        :return: 是否为最新版本
        :rtype: bool
        """
        logger.debug("[MANAGER][VERSION] 检查版本")

        try:

            async def check_fail() -> bool:
                """
                检查失败

                :return: 是否继续运行
                :rtype: bool
                """
                logger.error("检查版本更新失败")

                # 获取用户确认
                confirm = await answer(
                    questionary.confirm(
                        message="是否跳过版本检查继续运行?", default=False
                    )
                )
                if confirm:
                    logger.warning("已跳过版本检查, 建议手动检查版本")
                    return True

                return False

            logger.info(f"正在检查更新, 当前版本: {self.tag}")

            # 获取最新版本信息
            latest_info = await self.get_latest_info()
            if not latest_info:
                return await check_fail()

            # 解析最新版本信息
            latest_release_tag, latest_release_content = latest_info
            if not latest_release_tag or not latest_release_content:
                return await check_fail()

            # 有新版本
            if self.tag < latest_release_tag:
                logger.warning(
                    f"检测到新版本 {latest_release_tag}, 当前版本: {self.tag}"
                )
                logger.warning(
                    "请前往下载新版本: https://github.com/ChinoKou/UCourseAuto/releases/latest"
                )
                logger.info(f"版本 {latest_release_tag} 发布信息如下: ")
                print(latest_release_content)
                return False

            # 已是最新版本
            else:
                logger.success("当前版本已是最新版本")
                return True

        except Exception as e:
            return False
