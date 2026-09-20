# -*- coding: utf-8 -*-
import os
import datetime
import threading
from typing import Optional
from fastapi import Request
import auth as auth_module

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
CHECK_AUDIT_LOG_PATH = os.path.join(LOGS_DIR, "check_audit.log")

_log_lock = threading.Lock()

def get_current_user_info(request: Optional[Request]) -> tuple:
    """从 HTTP Request 标头中提取当前登录用户账号与角色"""
    if not request:
        return "系统操作者", "system", "127.0.0.1"

    # 1. 尝试从客户端 IP 提取
    client_ip = request.client.host if request.client else "未知IP"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # 2. 从 Authorization Header 提取 Token
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif request.headers.get("X-Auth-Token"):
        token = request.headers.get("X-Auth-Token").strip()

    if token:
        payload = auth_module._verify_token(token)
        if payload and payload.get("sub"):
            username = payload.get("sub")
            role = payload.get("role", "user")
            role_desc = "管理员" if role == "admin" else "核查员"
            return f"{username}({role_desc})", role, client_ip

    # 3. 尝试从自定义 Header X-Username 读取兜底
    custom_u = request.headers.get("X-Username")
    if custom_u:
        return f"{custom_u}(操作员)", "user", client_ip

    return "系统/未登录操作者", "guest", client_ip

def record_check_audit(
    module_type: str,
    action_type: str,
    target_desc: str,
    details: str = "",
    request: Optional[Request] = None,
    username: str = None
):
    """
    持久化记录内业、外业核查审计日志
    :param module_type: "内业核查" | "外业核查"
    :param action_type: 如 "保存内业评分"、"外业农户签名"、"导出附件8" 等
    :param target_desc: 核查对象描述（如 "涧溪镇 - 鲁南村"、"明东街道抹山村前吴组" 等）
    :param details: 具体记录内容（得分、打X项、问询项、文件路径等）
    :param request: FastAPI Request 对象
    :param username: 可显式覆盖操作人员用户名
    """
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if username:
            user_info = f"{username}(操作员)"
            client_ip = "127.0.0.1"
        else:
            user_info, _, client_ip = get_current_user_info(request)

        # 构造规整的单条审计日志
        log_line = (
            f"[{now_str}] [{module_type}] [账号: {user_info}] [IP: {client_ip}] "
            f"操作: {action_type} | 对象: {target_desc}"
        )
        if details:
            log_line += f" | 明细: {details}"

        with _log_lock:
            with open(CHECK_AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")

            # 同步按日期保留每日审计文件
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            daily_path = os.path.join(LOGS_DIR, f"check_audit_{today_str}.log")
            with open(daily_path, "a", encoding="utf-8") as f_daily:
                f_daily.write(log_line + "\n")

        print(f"[AUDIT] {log_line}")
    except Exception as e:
        print(f"写入核查审计日志失败: {e}")
