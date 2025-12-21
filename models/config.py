from pydantic import BaseModel, Field
from .course import ModelCourse

class UserConfig(BaseModel):
    """用户配置信息数据模型"""

    site: str = Field(title="站点")
    """站点"""
    username: str = Field(title="用户名")
    """用户名"""
    password: str = Field(title="密码")
    """密码"""
    token: str = "abc"  # 占位
    """鉴权令牌"""
    cookies: dict = Field(default_factory=dict)
    """Cookies"""
    courses: dict[int, ModelCourse] = Field(default_factory=dict)
    """课程信息"""


class ConfigModel(BaseModel):

    """配置信息数据模型"""

    class StudyTime(BaseModel):
        """学习时间数据模型"""

        class MinMaxTime(BaseModel):
            """时间范围"""

            min: int = 180
            """最小上报时间(s)"""
            max: int = 360
            """最大上报时间(s)"""

        question: MinMaxTime = Field(default_factory=MinMaxTime)
        """问题类型的上报时间范围"""
        document: MinMaxTime = Field(default_factory=MinMaxTime)
        """文档类型的上报时间范围"""
        content: MinMaxTime = Field(default_factory=MinMaxTime)
        """内容类型的上报时间范围"""

    debug: bool = False
    """调试模式"""
    active_user: str = ""
    """当前活跃用户"""
    users: dict[str, UserConfig] = Field(default_factory=dict)
    """用户信息"""
    study_time: StudyTime = Field(default_factory=StudyTime)
    """学习时间配置"""
    sleep_time: float = 1
    """休眠时间(s)"""
