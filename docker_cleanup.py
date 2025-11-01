#!/usr/bin/env python3
"""Docker清理脚本 - 每3小时清理一次无用的Docker资源"""

import logging
import subprocess
import time
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("docker_cleanup.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def run_docker_command(cmd: list[str]) -> tuple[int, str, str]:
    """运行Docker命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"命令超时: {' '.join(cmd)}")
        return -1, "", "Timeout"
    except Exception as e:
        logger.error(f"命令执行失败: {' '.join(cmd)}, 错误: {e}")
        return -1, "", str(e)


def get_docker_disk_usage():
    """获取Docker磁盘使用情况"""
    logger.info("检查Docker磁盘使用情况...")
    returncode, stdout, stderr = run_docker_command(["docker", "system", "df"])
    if returncode == 0:
        logger.info(f"Docker磁盘使用情况:\n{stdout}")
        return stdout
    else:
        logger.error(f"获取磁盘使用情况失败: {stderr}")
        return None


def cleanup_docker_resources():
    """清理Docker资源"""
    logger.info("开始清理Docker资源...")

    # 2. 清理未使用的镜像
    logger.info("清理未使用的镜像...")
    returncode, stdout, stderr = run_docker_command(["docker", "image", "prune", "-f", "-a"])
    if returncode == 0:
        logger.info(f"镜像清理完成: {stdout}")
    else:
        logger.error(f"镜像清理失败: {stderr}")

    # 3. 清理未使用的网络
    logger.info("清理未使用的网络...")
    returncode, stdout, stderr = run_docker_command(["docker", "network", "prune", "-f"])
    if returncode == 0:
        logger.info(f"网络清理完成: {stdout}")
    else:
        logger.error(f"网络清理失败: {stderr}")

    # 4. 清理构建缓存
    logger.info("清理构建缓存...")
    returncode, stdout, stderr = run_docker_command(["docker", "builder", "prune", "-f"])
    if returncode == 0:
        logger.info(f"构建缓存清理完成: {stdout}")
    else:
        logger.error(f"构建缓存清理失败: {stderr}")


def cleanup_old_images():
    """清理超过24小时的镜像"""
    logger.info("清理超过24小时的镜像...")

    # 获取所有镜像
    returncode, stdout, stderr = run_docker_command(
        ["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}"]
    )
    if returncode != 0:
        logger.error(f"获取镜像列表失败: {stderr}")
        return

    # 这里可以添加更复杂的逻辑来识别和删除旧镜像
    # 为了安全起见，我们只清理dangling镜像
    logger.info("清理dangling镜像...")
    returncode, stdout, stderr = run_docker_command(["docker", "image", "prune", "-f"])
    if returncode == 0:
        logger.info(f"Dangling镜像清理完成: {stdout}")
    else:
        logger.error(f"Dangling镜像清理失败: {stderr}")


def main():
    """主函数 - 每3小时运行一次清理"""
    logger.info("Docker清理脚本启动")

    while True:
        try:
            # 记录开始时间
            start_time = datetime.now()
            logger.info("等待3小时后进行下次清理...")
            time.sleep(3 * 60 * 60)  # 3小时 = 3 * 60 * 60 秒
            logger.info(f"开始清理任务 - {start_time}")

            # 获取清理前的磁盘使用情况
            get_docker_disk_usage()

            # 执行清理
            cleanup_docker_resources()
            cleanup_old_images()

            # 获取清理后的磁盘使用情况
            logger.info("清理完成，检查清理效果...")
            get_docker_disk_usage()

            # 计算清理耗时
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"清理任务完成 - 耗时: {duration}")

            # 等待3小时
            # logger.info("等待3小时后进行下次清理...")
            # time.sleep(3 * 60 * 60)  # 3小时 = 2 * 60 * 60 秒

        except KeyboardInterrupt:
            logger.info("收到中断信号，退出清理脚本")
            break
        except Exception as e:
            logger.error(f"清理过程中出现错误: {e}")
            logger.info("等待1小时后重试...")
            time.sleep(60 * 60)  # 1小时后重试


if __name__ == "__main__":
    main()
