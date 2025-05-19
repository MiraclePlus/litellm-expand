import logging
import sys

# ANSI颜色代码
class ColorCode:
    GREY = "\033[38;5;240m"
    BLUE = "\033[38;5;39m"
    GREEN = "\033[38;5;34m"
    YELLOW = "\033[38;5;220m"
    RED = "\033[38;5;196m"
    PURPLE = "\033[38;5;170m"
    CYAN = "\033[38;5;44m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

# 自定义带颜色的日志格式化器
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": ColorCode.BLUE,
        "INFO": ColorCode.GREEN,
        "WARNING": ColorCode.YELLOW,
        "ERROR": ColorCode.RED,
        "CRITICAL": ColorCode.PURPLE
    }
    
    def format(self, record):
        # 获取日志级别对应的颜色
        levelname = record.levelname
        levelcolor = self.COLORS.get(levelname, ColorCode.RESET)
        
        # 设置时间戳颜色
        time_color = ColorCode.GREY
        
        # 设置名称颜色
        name_color = ColorCode.CYAN
        
        # 创建格式化字符串
        format_str = (
            f"{time_color}%(asctime)s{ColorCode.RESET} "
            f"{levelcolor}%(levelname)s{ColorCode.RESET}: "
            f"{name_color}%(name)s{ColorCode.RESET} "
            f"%(message)s"
        )
        
        # 创建临时格式化器
        formatter = logging.Formatter(
            format_str,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        return formatter.format(record)

# 创建并配置控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter())

# 配置根日志记录器，影响所有未明确配置的日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# 清除可能存在的处理器以避免重复日志
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
root_logger.addHandler(console_handler)

# 创建应用日志记录器
logger = logging.getLogger("litellm")
logger.setLevel(logging.DEBUG)

# 统一配置其他常用模块的日志格式
module_loggers = [
    "uvicorn", 
    "uvicorn.access", 
    "fastapi", 
    "apscheduler.scheduler",
    "sqlalchemy.engine"
]

for module_name in module_loggers:
    module_logger = logging.getLogger(module_name)
    module_logger.handlers = []  # 清除默认处理器
    # 让模块日志记录器使用根日志记录器的设置
    module_logger.propagate = True
