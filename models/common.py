from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from .config import UserConfig

if TYPE_CHECKING:
    from apis import LoginAPI


class APIUrl(BaseModel):
    """API地址数据模型"""

    base_api: str
    course_api: str
    ua_api: str

    @classmethod
    def create(cls, site: str) -> "APIUrl":
        """创建实例"""
        url_map = {
            "ulearning": {
                "base_api": "https://ulearning.cn",
                "course_api": "https://courseapi.ulearning.cn",
                "ua_api": "https://api.ulearning.cn",
            },
            "dgut": {
                "base_api": "https://lms.dgut.edu.cn",
                "course_api": "https://lms.dgut.edu.cn/courseapi",
                "ua_api": "https://ua.dgut.edu.cn/uaapi",
            },
        }
        return cls(**url_map[site])


@dataclass
class UserAPI:
    """用户API"""

    user_config: UserConfig
    login_api: "LoginAPI"
