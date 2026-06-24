#!/usr/bin/env bash
# 手写数字视频识别 — 启动脚本 (Linux/macOS)
# 自动定位 digit_recognition conda 环境

set -e

ENV_NAME="digit_recognition"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 尝试多个可能的 conda 路径
CONDA_PATHS=(
    "$HOME/conda/envs/$ENV_NAME/bin/python"
    "$HOME/anaconda3/envs/$ENV_NAME/bin/python"
    "$HOME/miniconda3/envs/$ENV_NAME/bin/python"
    "$HOME/.conda/envs/$ENV_NAME/bin/python"
    "/opt/conda/envs/$ENV_NAME/bin/python"
    "/opt/anaconda3/envs/$ENV_NAME/bin/python"
)

PYTHON_EXE=""

for p in "${CONDA_PATHS[@]}"; do
    if [ -x "$p" ]; then
        PYTHON_EXE="$p"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    # 尝试通过 conda 命令获取路径
    if command -v conda &> /dev/null; then
        CONDA_PREFIX=$(conda info --envs 2>/dev/null | grep "^$ENV_NAME " | awk '{print $NF}')
        if [ -n "$CONDA_PREFIX" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
            PYTHON_EXE="$CONDA_PREFIX/bin/python"
        fi
    fi
fi

if [ -z "$PYTHON_EXE" ]; then
    # 最后回退到系统 python3
    if command -v python3 &> /dev/null; then
        echo "[WARN] 未找到 $ENV_NAME conda 环境，使用系统 python3"
        PYTHON_EXE="python3"
    else
        echo "[ERROR] 找不到 $ENV_NAME conda 环境，且系统无 python3"
        echo "请先执行: conda create -n $ENV_NAME python=3.11 -y"
        echo "或安装 python3 及所需依赖"
        exit 1
    fi
else
    echo "[INFO] 使用环境: $PYTHON_EXE"
fi

cd "$SCRIPT_DIR"
exec "$PYTHON_EXE" "$SCRIPT_DIR/src/main.py" "$@"
