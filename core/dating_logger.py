import logging
import sys

class ColorFormatter(logging.Formatter):
    """Bộ tô màu cho Terminal Console"""
    COLORS = {
        logging.DEBUG: "\x1b[90m",     # Xám mờ
        logging.INFO: "\x1b[36m",      # Xanh lơ (Cyan)
        logging.WARNING: "\x1b[33m",   # Vàng
        logging.ERROR: "\x1b[31m",     # Đỏ
        logging.CRITICAL: "\x1b[31;1m" # Đỏ đậm chót vót
    }
    RESET = "\x1b[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = self.formatTime(record, "%H:%M:%S")
        # Định dạng: [MÀU] ERROR [RESET] 14:05:01 [dating.gate] Lỗi gì đó...
        log_fmt = f"{color}{record.levelname:<5}{self.RESET} \x1b[90m{timestamp}\x1b[0m [{record.name}] {record.getMessage()}"
        return log_fmt

def get_logger(name: str) -> logging.Logger:
    """Tạo logger đồng bộ cho mọi module"""
    logger = logging.getLogger(name)
    
    # Chỉ add handler nếu chưa có để tránh in log đúp
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO) # Sếp có thể đổi thành DEBUG nếu muốn soi lỗi
        logger.propagate = False
        
    return logger
