from traceback import format_exc
from typing import TYPE_CHECKING

import questionary
from loguru import logger

from .http_client import HttpClient
from .logger_manager import LoggerManager
from utils import answer

if TYPE_CHECKING:
    from config import Config


class ConfigManager:
    """配置管理类"""

    def __init__(
        self, config: "Config", client: HttpClient, logger_manager: LoggerManager
    ) -> None:
        """
        配置管理类初始化

        :param config: 配置对象
        :type config: "Config"
        :param client: 内部Http客户端对象
        :type client: HttpClient
        """

        self.config = config
        self.client = client
        self.logger_manager = logger_manager

    async def menu(self) -> None:
        """配置管理菜单"""
        logger.debug("[MANAGER][CONFIG] 配置管理菜单")

        # 初始化选项
        choices = [
            "修改调试模式",
            "修改上报冷却",
            "重新读取配置文件",
            "重新写入配置文件",
            "返回",
        ]
        choices_map = {
            "修改调试模式": self.__change_debug_mode,
            "修改上报冷却": self.__change_sleep_time,
            "重新读取配置文件": self.__reload_config,
            "重新写入配置文件": self.__rewrite_config,
            "返回": lambda: None,
        }

        try:
            while True:
                choice = await answer(
                    questionary.select(
                        message="[配置管理菜单] 请选择",
                        choices=choices,
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                if choice == "返回":
                    return None

                await choices_map[choice]()

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][CONFIG] 配置管理菜单出错: {e}")
            return None

    async def __change_debug_mode(self) -> None:
        """修改调试模式"""
        logger.debug("[MANAGER][CONFIG] 修改调试模式")

        try:
            # 获取用户选择
            choice = await answer(
                questionary.select(
                    message="请选择调试模式",
                    choices=["开启", "关闭", "返回"],
                    instruction="(使用方向键选择, 回车键确认)",
                )
            )
            if choice == "返回":
                return None

            if choice == "开启":
                # 修改配置文件
                self.config.debug = True
                self.config.save()

                # 修改日志输出
                self.logger_manager.set_logger(debug=True)

                # 重新创建 HttpClient 内部的客户端
                if not await self.client.re_create_client(debug=True):
                    raise

                logger.success("已开启调试模式")

            elif choice == "关闭":
                # 修改配置文件
                self.config.debug = False
                self.config.save()

                # 修改日志输出
                self.logger_manager.set_logger(debug=False)

                # 重新创建 HttpClient 内部的客户端
                if not await self.client.re_create_client(debug=False):
                    raise

                logger.success("已关闭调试模式")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][CONFIG] 修改调试模式出错: {e}")
            return None

    async def __change_sleep_time(self) -> None:
        """修改上报冷却"""
        logger.debug("[MANAGER][CONFIG] 修改上报冷却")

        try:
            current_sleep_time = self.config.sleep_time
            new_sleep_time = await answer(
                questionary.text(
                    message=f"[当前值: {current_sleep_time}s]请输入新的上报冷却时间(秒):",
                    default=str(1.0),
                    validate=lambda x: x.replace(".", "", 1).isdigit()
                    and 0 <= float(x) <= 10
                    or "请输入正确的数字(0~10)",
                )
            )
            self.config.sleep_time = float(new_sleep_time)
            self.config.save()

            logger.success(f"已修改上报冷却时间为 {self.config.sleep_time}s")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][CONFIG] 修改上报冷却出错: {e}")
            return None

    async def __reload_config(self) -> None:
        """重新读取配置文件"""
        logger.debug("[MANAGER][CONFIG] 重新读取配置文件")

        try:
            reload_status = self.config.reload()
            if reload_status:
                logger.success("已重新读取配置文件")

            else:
                logger.warning("重新读取配置文件失败")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][CONFIG] 重新读取配置文件出错: {e}")
            return None

    async def __rewrite_config(self) -> None:
        """重新写入配置文件"""
        logger.debug("[MANAGER][CONFIG] 重新写入配置文件")

        try:
            self.config.save()
            logger.success("已重新写入配置文件")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][CONFIG] 重新写入配置文件出错: {e}")
            return None
