import asyncio
from collections.abc import Callable
from traceback import format_exc
from typing import TYPE_CHECKING

import questionary
from loguru import logger
from apis import LoginAPI
from models import UserAPI, UserConfig
from utils import answer

from .http_client import HttpClient

if TYPE_CHECKING:
    from config import Config


class UserManager:
    """用户管理类"""

    def __init__(self, config: "Config") -> None:
        """
        用户管理类初始化

        :param config: 配置对象
        :type config: "Config"
        """

        self.config: "Config" = config
        self.active_client: HttpClient | None = None
        self.users: dict[str, UserAPI] = {}
        self.sites: dict[str, dict[str, str]] = {
            "主站": {"name": "ulearning", "url": "ulearning.cn"},
            "东莞理工学院": {"name": "dgut", "url": "lms.dgut.edu.cn"},
        }

    async def menu(self) -> None:
        """用户管理菜单"""
        logger.debug("[MANAGER][USER] 进入用户管理菜单")

        # 初始化选项
        choices: list[str] = [
            "添加用户",
            "切换用户",
            "删除用户",
            "修改用户信息",
            "刷新登录状态",
            "检查登录状态",
            "返回",
        ]
        choices_map: dict[str, Callable] = {
            "添加用户": self.__add_user,
            "切换用户": self.__switch_user,
            "删除用户": self.__remove_user,
            "修改用户信息": self.__modify_user,
            "刷新登录状态": self.refresh_login_status,
            "检查登录状态": self.check_login_status,
            "返回": lambda: None,
        }

        try:
            while True:
                choice = await answer(
                    questionary.select(
                        message="[用户管理菜单] 请选择",
                        choices=choices,
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                if choice == "返回":
                    return None

                await choices_map[choice]()

        except KeyboardInterrupt as e:
            logger.info("[MANAGER][USER] 强制退出用户管理")
            return None

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 用户管理出现异常: {e}")
            return None

    async def __login(self, user_config: UserConfig) -> bool:
        """
        执行登录

        :param user_config: 用户配置对象
        :type user_config: UserConfig
        :return: 是否登录成功
        :rtype: bool

        """
        logger.debug(f"[MANAGER][USER] 登录用户: {user_config.username}")

        try:
            # 创建Http客户端
            http_client = HttpClient(debug=self.config.debug)

            # 设置Cookie
            if user_config.cookies:
                http_client.set_cookies(cookies=user_config.cookies)

            # 设置Token
            if user_config.token != "abc":
                http_client.set_token(token=user_config.token)

            # 创建登录API
            login_api = LoginAPI(
                username=user_config.username, config=self.config, client=http_client
            )

            # 检查登录状态
            if await login_api.check_login_status():
                # 设置活跃用户和Http客户端
                self.config.active_user = user_config.username
                self.config.save()
                self.active_client = http_client

                # 设置用户API
                self.users[user_config.username] = UserAPI(
                    user_config=user_config, login_api=login_api
                )
                return True

            # 登录
            user_info_resp = await login_api.login()

            # 保存用户信息
            if user_info_resp:
                # 设置活跃用户和Http客户端
                self.config.active_user = user_config.username
                self.active_client = http_client

                # 设置用户API
                self.users[user_config.username] = UserAPI(
                    user_config=user_config, login_api=login_api
                )

                # 保存用户信息
                cookies = http_client.get_cookies()
                user_config.cookies = cookies
                user_config.token = user_info_resp.authorization
                self.config.active_user = user_config.username
                self.config.save()

                logger.success(f"登录成功: {user_config.username}")

                return True

            else:
                logger.error("登录失败")

            return False

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 登录出错: {e}")
            return False

    async def __add_user(self) -> bool:
        """添加账号"""
        logger.debug("[MANAGER][USER] 添加账号")

        try:
            while True:
                # 获取站点和用户名
                site: str = await answer(
                    questionary.select(
                        message="请选择站点",
                        choices=[k for k, v in self.sites.items()],
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )
                username: str = await answer(
                    questionary.text(
                        message="请输入用户名",
                        validate=lambda x: len(x) > 0 or "用户名不可为空",
                    )
                )

                # 覆盖确认
                if username in self.config.users:
                    if not await answer(
                        questionary.confirm(
                            message="用户已存在, 是否覆盖?", default=False
                        )
                    ):
                        break

                # 获取密码
                password: str = await answer(
                    questionary.password(
                        message="请输入密码",
                        validate=lambda x: len(x) > 0 or "密码不可为空",
                    )
                )

                # 初始化用户配置信息实例
                user_config = UserConfig(
                    username=username, password=password, site=self.sites[site]["name"]
                )

                self.config.users[user_config.username] = user_config

                retry = 0
                while True:
                    # 登录
                    if await self.__login(user_config=user_config):
                        await self.refresh_login_status()
                        return True

                    if retry >= 3:
                        break

                    retry += 1
                    await asyncio.sleep(1)

                self.config.users.pop(user_config.username)

            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 添加用户出错: {e}")
            return False

    async def __remove_user(self) -> bool:
        logger.debug("[MANAGER][USER] 删除账号")

        try:
            while True:
                # 初始化用户选择
                username_choices = [k for k, v in self.config.users.items()]
                username_choices.remove(self.config.active_user)
                username_choices.append("返回")

                # 获取用户选择
                username: str = await answer(
                    questionary.select(
                        message="请选择要删除的账号",
                        choices=username_choices,
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                if username == "返回":
                    return True

                if username == self.config.active_user:
                    logger.warning("不允许删除当前登录的账号")
                    continue

                # 删除用户信息
                self.config.users.pop(username)
                self.config.save()

                if username in self.users:
                    self.users.pop(username)

                logger.success(f"成功删除账号: {username}")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 删除用户出错: {e}")
            return False

    async def __switch_user(self) -> bool:
        logger.debug("[MANAGER][USER] 选择用户")

        try:
            while True:
                # 获取用户选择
                username: str = await answer(
                    questionary.select(
                        message="请选择用户",
                        choices=[k for k, v in self.config.users.items()]
                        + ["添加新账号", "修改账号信息", "返回"],
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                if username == "添加新账号":
                    return await self.__add_user()

                elif username == "修改账号信息":
                    return await self.__modify_user()

                elif username == "返回":
                    return False

                user = self.config.users[username]
                if await self.__login(user):
                    logger.success(f"登录成功: {username}")
                    break

                logger.warning("登录失败")

            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 选择用户出错: {e}")
            return False

    async def __modify_user(self) -> bool:
        logger.debug("[MANAGER][USER] 修改用户信息")

        try:
            while True:
                # 获取用户选择
                username: str = await answer(
                    questionary.select(
                        message="请选择要修改的用户",
                        choices=[k for k, v in self.config.users.items()] + ["返回"],
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                if username == "返回":
                    break

                while True:
                    # 获取 UserConfig 实例
                    user = self.config.users[username]
                    raw_user_config = UserConfig(
                        site=user.site,
                        username=user.username,
                        password=user.password,
                        token=user.token,
                        cookies=user.cookies,
                        courses=user.courses,
                    )

                    # 初始化属性选择
                    attr_choices = []
                    accept_attrs = ["site", "password"]

                    # 获取用户配置数据模型字段
                    for field_name, field_info in UserConfig.model_fields.items():
                        # 忽略掉无法修改的属性
                        if field_name not in accept_attrs:
                            continue

                        # 获取字段值
                        field_value = getattr(user, field_name)

                        # 密码脱敏
                        if field_name == "password":
                            field_value = (
                                field_value[:2]
                                + "*" * (len(field_value) - 4)
                                + field_value[-2:]
                            )

                        # 添加属性选择
                        attr_choices.append(
                            f"{field_name}: {field_info.title} (当前值: {field_value})"
                        )

                    attr_choices.append("返回")

                    # 获取用户选择
                    attr: str = await answer(
                        questionary.select(
                            message="请选择要修改的属性",
                            choices=attr_choices,
                            instruction="(使用方向键选择, 回车键确认)",
                        )
                    )
                    if attr == "返回":
                        break

                    # 解析选择
                    attr_name = attr.split(":")[0].strip()

                    # 获取用户输入的新属性值
                    if attr_name == "site":
                        attr_value = await answer(
                            questionary.select(
                                message="请选择站点",
                                choices=[k for k, v in self.sites.items()],
                                instruction="(使用方向键选择, 回车键确认)",
                            )
                        )
                        attr_value = self.sites[attr_value]["name"]

                    elif attr_name == "password":
                        attr_value = await answer(
                            questionary.password(
                                message=f"请输入属性 {attr_name} 的值",
                                validate=lambda x: len(x) > 0 or "密码不可为空",
                            )
                        )

                    else:
                        raise

                    # 设置属性值
                    setattr(user, attr_name, attr_value)

                    # 去除 token 和 cookies
                    setattr(user, "token", "abc")
                    setattr(user, "cookies", {})

                    # 执行登录对修改进行校验
                    if await self.__login(user):
                        # __login() 执行成功会自动保存配置信息
                        await self.refresh_login_status()
                        logger.success(f"成功修改属性 {attr_name} 的值")
                        break

                    else:
                        logger.warning(f"修改属性 {attr_name} 的值失败")

                        # 有很多地方引用了 user 对象, 这里需使用 setattr 恢复原始值
                        setattr(user, attr_name, getattr(raw_user_config, attr_name))
                        setattr(user, "token", getattr(raw_user_config, "token"))
                        setattr(user, "cookies", getattr(raw_user_config, "cookies"))
                        self.config.save()

            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 修改用户信息出错: {e}")
            return False

    async def refresh_login_status(self) -> bool:
        """刷新登录状态"""
        logger.debug("[MANAGER][USER] 刷新登录状态")

        try:
            return await self.__login(self.config.users[self.config.active_user])

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 刷新登录状态出错: {e}")
            return False

    async def check_login_status(self) -> bool:
        """检查登录状态"""
        logger.debug("[MANAGER][USER] 检查登录状态")

        try:
            # 检查配置文件中的活跃用户是否存在于内存中的用户管理
            if self.config.active_user in self.users:

                # 获取 LoginAPI 对象
                login_api = self.users[self.config.active_user].login_api
                if not login_api:
                    raise

                # 检查登录状态
                login_status = await login_api.check_login_status()
                return login_status

            # 配置文件中的活跃用户存在于配置文件中
            elif self.config.active_user in self.config.users:
                # 执行登录
                return await self.refresh_login_status()

            # 配置文件不存在活跃用户
            elif not self.config.users:
                # 全新启动, 添加用户
                logger.info("全新启动, 添加新用户")
                return await self.__add_user()

            # 其他情况, 如活跃用户为空时
            else:
                return await self.__switch_user()

            return False

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][USER] 检查登录状态出错: {e}")
            return False

    async def get_client(self) -> HttpClient | None:
        """获取 HttpClient 对象"""
        logger.debug("[MANAGER][USER] 获取 HttpClient 对象")

        try:
            if hasattr(self, "active_client") and self.active_client:
                return self.active_client

            return None

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][USER] 获取 HttpClient 对象出错: {e}"
            )
            return None
