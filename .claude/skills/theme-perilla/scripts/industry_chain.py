#!/usr/bin/env python3
"""产业链图谱构建助手
━━━━━━━━━━━━━━━━━━━━
根据热门主题，构建上游/中游/下游产业链图谱。

用法：
    python scripts/industry_chain.py --theme AI算力 --output chain.json
"""

import argparse
import json
from pathlib import Path

# 预定义的产业链图谱（可扩展）
INDUSTRY_CHAINS = {
    "AI算力": {
        "upstream": [
            {"segment": "芯片设计", "companies": [
                {"code": "688041", "name": "海光信息", "niche": "国产GPU/DCU"},
                {"code": "688256", "name": "寒武纪", "niche": "AI芯片"},
                {"code": "300474", "name": "景嘉微", "niche": "军用GPU"},
            ]},
            {"segment": "半导体设备", "companies": [
                {"code": "002371", "name": "北方华创", "niche": "刻蚀/薄膜设备"},
                {"code": "688012", "name": "中微公司", "niche": "刻蚀设备"},
                {"code": "688072", "name": "拓荆科技", "niche": "薄膜设备"},
            ]},
        ],
        "midstream": [
            {"segment": "芯片制造", "companies": [
                {"code": "688981", "name": "中芯国际", "niche": "晶圆代工龙头"},
                {"code": "688289", "name": "澜起科技", "niche": "接口芯片"},
            ]},
            {"segment": "封装测试", "companies": [
                {"code": "600584", "name": "长电科技", "niche": "封测龙头"},
            ]},
        ],
        "downstream": [
            {"segment": "AI服务器", "companies": [
                {"code": "000977", "name": "浪潮信息", "niche": "AI服务器龙头"},
                {"code": "603019", "name": "中科曙光", "niche": "高性能计算"},
            ]},
            {"segment": "数据中心", "companies": [
                {"code": "603881", "name": "数据港", "niche": "IDC运营"},
            ]},
        ],
    },
    "新能源": {
        "upstream": [
            {"segment": "原材料", "companies": [
                {"code": "002466", "name": "天齐锂业", "niche": "锂矿龙头"},
                {"code": "600390", "name": "五矿稀土", "niche": "稀土资源"},
            ]},
            {"segment": "电池材料", "companies": [
                {"code": "300073", "name": "当升科技", "niche": "正极材料"},
                {"code": "603799", "name": "华友钴业", "niche": "钴新材料"},
            ]},
        ],
        "midstream": [
            {"segment": "电池制造", "companies": [
                {"code": "300750", "name": "宁德时代", "niche": "动力电池龙头"},
                {"code": "002074", "name": "国轩高科", "niche": "动力电池"},
            ]},
        ],
        "downstream": [
            {"segment": "新能源汽车", "companies": [
                {"code": "002594", "name": "比亚迪", "niche": "新能源车龙头"},
                {"code": "601127", "name": "赛力斯", "niche": "华为智选车"},
            ]},
            {"segment": "储能", "companies": [
                {"code": "002733", "name": "雄韬股份", "niche": "储能电池"},
            ]},
        ],
    },
    "半导体": {
        "upstream": [
            {"segment": "EDA工具", "companies": [
                {"code": "688981", "name": "中芯国际", "niche": "国产EDA领先"},
            ]},
            {"segment": "半导体材料", "companies": [
                {"code": "300661", "name": "江丰电子", "niche": "靶材"},
                {"code": "002409", "name": "雅克科技", "niche": "电子特气"},
            ]},
            {"segment": "设备", "companies": [
                {"code": "002371", "name": "北方华创", "niche": "半导体设备龙头"},
                {"code": "688012", "name": "中微公司", "niche": "刻蚀设备"},
            ]},
        ],
        "midstream": [
            {"segment": "芯片设计", "companies": [
                {"code": "688041", "name": "海光信息", "niche": "国产GPU"},
                {"code": "688256", "name": "寒武纪", "niche": "AI芯片"},
            ]},
            {"segment": "芯片制造", "companies": [
                {"code": "688981", "name": "中芯国际", "niche": "晶圆代工龙头"},
            ]},
            {"segment": "封测", "companies": [
                {"code": "600584", "name": "长电科技", "niche": "封测龙头"},
            ]},
        ],
        "downstream": [
            {"segment": "消费电子", "companies": [
                {"code": "002475", "name": "立讯精密", "niche": "电子制造龙头"},
            ]},
        ],
    },
}


def build_chain(theme: str) -> dict:
    """构建产业链图谱。"""
    chain = INDUSTRY_CHAINS.get(theme, {})

    if not chain:
        return {
            "theme": theme,
            "status": "not_found",
            "message": f"暂无 {theme} 的产业链图谱，请使用 MCP 搜索构建",
        }

    # 统计
    all_companies = []
    for segment_list in chain.values():
        for segment in segment_list:
            all_companies.extend(segment.get("companies", []))

    unique_codes = set(c["code"] for c in all_companies)

    return {
        "theme": theme,
        "status": "found",
        "upstream": [s["companies"] for s in chain.get("upstream", [])],
        "midstream": [s["companies"] for s in chain.get("midstream", [])],
        "downstream": [s["companies"] for s in chain.get("downstream", [])],
        "total_companies": len(unique_codes),
    }


def load_chain_from_file(theme: str, base_dir: Path) -> dict:
    """从 references/industry-chains/{theme}.md 加载产业链图谱。"""
    safe_name = theme.replace("/", "_").replace("\\", "_")
    chain_file = base_dir / "references" / "industry-chains" / f"{safe_name}.md"

    if not chain_file.exists():
        return build_chain(theme)

    content = chain_file.read_text(encoding="utf-8")
    return {
        "theme": theme,
        "status": "loaded_from_file",
        "source": str(chain_file),
        "content": content,
    }


def main():
    parser = argparse.ArgumentParser(description="产业链图谱构建助手")
    parser.add_argument("--theme", required=True, help="热门主题")
    parser.add_argument("--output", help="输出文件路径")
    args = parser.parse_args()

    result = build_chain(args.theme)
    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
