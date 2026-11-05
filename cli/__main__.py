"""@brief `python -m cli` 入口（与独立脚本、主程序 --cli 分流共用实现）。"""

import sys

from . import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
