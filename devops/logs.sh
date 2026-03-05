#!/bin/bash
# ============================================
#  WeClaw 日志查看工具
#  快速查看服务器上的 pm2 日志
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF_FILE="${SCRIPT_DIR}/deploy.conf"

# 加载配置
if [ ! -f "$CONF_FILE" ]; then
    echo -e "${RED}[错误]${NC} 未找到配置文件: ${CONF_FILE}"
    exit 1
fi

source "$CONF_FILE"

# 打印横幅
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════╗"
    echo "║         📋 WeClaw 日志查看工具           ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -o, --out [行数]     查看标准输出日志 (默认 50 行)"
    echo "  -e, --error [行数]   查看错误日志 (默认 50 行)"
    echo "  -f, --follow         实时跟踪日志 (类似 tail -f)"
    echo "  -s, --search <关键词> 搜索日志中的关键词"
    echo "  -a, --all            同时显示标准输出和错误日志"
    echo "  -c, --clear          清空日志文件"
    echo "  -h, --help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -o 100           # 查看最近 100 行标准输出"
    echo "  $0 -e               # 查看最近 50 行错误日志"
    echo "  $0 -f               # 实时跟踪日志"
    echo "  $0 -s '张家港'      # 搜索包含'张家港'的日志"
    echo "  $0 -a               # 同时查看标准输出和错误日志"
}

# 执行远程命令
remote_exec() {
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no -p "$SERVER_PORT" \
        "${SERVER_USER}@${SERVER_IP}" "$@"
}

# 查看标准输出日志
view_out_log() {
    local lines=${1:-50}
    echo -e "${BLUE}[标准输出]${NC} 最近 ${lines} 行:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    remote_exec "cat /root/.pm2/logs/${SERVICE_NAME}-out.log | tail -${lines}"
}

# 查看错误日志
view_error_log() {
    local lines=${1:-50}
    echo -e "${RED}[错误日志]${NC} 最近 ${lines} 行:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    remote_exec "cat /root/.pm2/logs/${SERVICE_NAME}-error.log | tail -${lines}"
}

# 实时跟踪日志
follow_logs() {
    echo -e "${GREEN}[实时跟踪]${NC} 按 Ctrl+C 退出"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    remote_exec "tail -f /root/.pm2/logs/${SERVICE_NAME}-out.log"
}

# 搜索日志
search_logs() {
    local keyword="$1"
    echo -e "${YELLOW}[搜索]${NC} 关键词: ${keyword}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}[标准输出]${NC}"
    remote_exec "grep --color=always '${keyword}' /root/.pm2/logs/${SERVICE_NAME}-out.log | tail -50 || echo '未找到匹配项'"
    echo ""
    echo -e "${RED}[错误日志]${NC}"
    remote_exec "grep --color=always '${keyword}' /root/.pm2/logs/${SERVICE_NAME}-error.log | tail -50 || echo '未找到匹配项'"
}

# 清空日志
clear_logs() {
    echo -e "${YELLOW}[警告]${NC} 即将清空所有日志文件"
    read -p "确认清空？[y/N]: " answer
    case $answer in
        [Yy]* )
            remote_exec "source ~/.nvm/nvm.sh 2>/dev/null; pm2 flush ${SERVICE_NAME}"
            echo -e "${GREEN}[成功]${NC} 日志已清空"
            ;;
        * )
            echo "已取消"
            ;;
    esac
}

# 主流程
main() {
    print_banner

    # 无参数时显示帮助
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    # 解析参数
    while [ $# -gt 0 ]; do
        case "$1" in
            -o|--out)
                shift
                view_out_log "${1:-50}"
                exit 0
                ;;
            -e|--error)
                shift
                view_error_log "${1:-50}"
                exit 0
                ;;
            -f|--follow)
                follow_logs
                exit 0
                ;;
            -s|--search)
                shift
                if [ -z "$1" ]; then
                    echo -e "${RED}[错误]${NC} 请提供搜索关键词"
                    exit 1
                fi
                search_logs "$1"
                exit 0
                ;;
            -a|--all)
                shift
                lines="${1:-50}"
                view_out_log "$lines"
                echo ""
                view_error_log "$lines"
                exit 0
                ;;
            -c|--clear)
                clear_logs
                exit 0
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}[错误]${NC} 未知选项: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done
}

main "$@"
