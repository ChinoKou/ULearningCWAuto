import os
import time
from sys import stderr

from loguru import logger


class LoggerManager:
    """日志管理类"""

    def __init__(self, dir_name: str = "ucourse_logs") -> None:
        """
        日志管理类初始化

        :param dir_name: 日志目录名
        :type dir_name: str
        """
        # 创建日志目录
        log_dir = os.path.join(os.getcwd(), dir_name)
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        # 初始化日志配置
        start_time = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        self.log_file = os.path.join(log_dir, f"{start_time}.log")
        self.log_format = "<green>{time:MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <level>{message}</level>"

    def set_logger(self, debug=False) -> None:
        """设置日志"""

        # 获取日志等级
        log_level = "DEBUG" if debug else "INFO"

        # 修改日志配置
        logger.remove()
        for sink, level in {stderr: log_level, self.log_file: "DEBUG"}.items():
            logger.add(sink=sink, level=level, format=self.log_format)
