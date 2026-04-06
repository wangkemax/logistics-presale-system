"""Seed the knowledge base with sample logistics industry data.

Usage:
    python -m app.scripts.seed_knowledge
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.core.database import AsyncSessionLocal
from app.models.models import KnowledgeEntry

SEED_DATA = [
    # ── Automation Cases ──
    {
        "category": "automation_case",
        "title": "电商仓储 AGV 拣选系统实施案例",
        "content": (
            "项目背景：某大型电商平台华东仓，面积 30,000 平米，日均订单 50,000 单，SKU 数量 80,000+。"
            "痛点：人工拣选效率低（60 单/人/小时），旺季招工难，错拣率 0.3%。\n\n"
            "解决方案：部署 200 台货架搬运 AGV（类 Kiva 系统），采用『货到人』拣选模式。"
            "投资 2,800 万元（含 AGV、货架改造、调度系统）。\n\n"
            "实施效果：拣选效率提升至 300 单/人/小时（提升 5 倍），人员从 200 人减至 60 人，"
            "错拣率降至 0.01%，ROI 18 个月，年节省人力成本 1,200 万元。"
        ),
        "tags": ["AGV", "电商", "货到人", "拣选", "华东"],
    },
    {
        "category": "automation_case",
        "title": "冷链医药仓 AS/RS 自动化立体库案例",
        "content": (
            "项目背景：某医药流通企业，冷链仓 8,000 平米，需 2-8°C 恒温存储，SKU 5,000+，"
            "合规要求 GSP 全程追溯。\n\n"
            "解决方案：6 巷道 AS/RS 立体库（高 18 米，6,000 货位），配合输送线和自动分拣。"
            "投资 4,500 万元。\n\n"
            "实施效果：存储密度提升 4 倍，减少冷库面积需求 60%，节省年制冷费用 300 万元。"
            "库存准确率 99.99%，满足 GSP 要求，ROI 24 个月。"
        ),
        "tags": ["AS/RS", "冷链", "医药", "立体库", "GSP"],
    },
    {
        "category": "automation_case",
        "title": "快消品分拣中心自动化输送分拣系统",
        "content": (
            "项目背景：某快消品企业全国分拨中心，日均处理 200,000 件，覆盖 500 个终端门店。\n\n"
            "解决方案：交叉带分拣机（300 个格口）+ 螺旋输送机 + 自动扫码称重，支持多品类混合分拣。"
            "投资 3,200 万元。\n\n"
            "实施效果：分拣效率 18,000 件/小时，准确率 99.98%，人员减少 70%，"
            "支持次日达配送 SLA，ROI 20 个月。"
        ),
        "tags": ["交叉带分拣", "快消", "分拨中心", "输送线"],
    },

    # ── Cost Models ──
    {
        "category": "cost_model",
        "title": "华东地区标准仓储成本基准 (2025)",
        "content": (
            "区域：上海/苏州/杭州/嘉兴\n\n"
            "场地租金：一线城市 1.5-2.0 元/㎡/天，二线城市 0.8-1.2 元/㎡/天\n"
            "人力成本：仓管员 5,500-7,000 元/月，叉车工 6,500-8,000 元/月，"
            "分拣员 5,000-6,500 元/月，管理人员 12,000-18,000 元/月\n"
            "设备折旧：叉车 15-25 万/台（5 年折旧），货架 200-500 元/组（10 年折旧）\n"
            "WMS 系统：SaaS 模式 2-5 万/年，私有化部署 30-80 万一次性\n"
            "水电物业：3-5 元/㎡/月\n"
            "耗材包装：0.5-2.0 元/单\n\n"
            "人效基准：标准件拣选 80-120 单/人/小时，"
            "带自动化设备可达 200-400 单/人/小时"
        ),
        "tags": ["华东", "成本基准", "租金", "人力成本", "2025"],
    },
    {
        "category": "cost_model",
        "title": "自动化设备投资成本参考 (2025)",
        "content": (
            "AGV/AMR：\n"
            "  - 货架搬运 AGV（类 Kiva）：8-15 万/台\n"
            "  - 料箱搬运 AMR：12-20 万/台\n"
            "  - 叉车式 AGV：25-40 万/台\n\n"
            "AS/RS 立体库：\n"
            "  - 单深位货架堆垛机：800-1,200 万/巷道\n"
            "  - 多穿/四向车系统：500-800 万/巷道\n"
            "  - Miniload（料箱立体库）：400-600 万/巷道\n\n"
            "分拣系统：\n"
            "  - 交叉带分拣机：8-15 万/格口\n"
            "  - 滑块分拣机：5-8 万/格口\n"
            "  - 摆轮分拣：2-4 万/路口\n\n"
            "输送线：800-2,000 元/米（含安装）\n"
            "电子标签拣选（PTL）：500-1,000 元/格口\n"
            "语音拣选系统：3,000-5,000 元/终端"
        ),
        "tags": ["自动化", "AGV", "AS/RS", "分拣", "设备成本", "2025"],
    },

    # ── Logistics Cases ──
    {
        "category": "logistics_case",
        "title": "某知名家电品牌全国仓配一体化项目",
        "content": (
            "客户：国内 Top3 家电品牌\n"
            "项目规模：6 个 RDC（区域配送中心），总面积 180,000 ㎡\n"
            "业务量：日均 80,000 单，覆盖全国 2,000+ 终端门店\n\n"
            "解决方案要点：\n"
            "1. 仓网规划：6 个 RDC 分布在华东/华南/华北/华中/西南/东北\n"
            "2. 存储方案：大件（冰箱/洗衣机）地堆存储 + 中小件（小家电）货架存储\n"
            "3. 配送模式：干线运输 + 城市配送 + 末端安装\n"
            "4. 技术系统：统一 WMS + TMS + OMS，与客户 ERP 对接\n"
            "5. 增值服务：开箱验货、安装调试、旧机回收\n\n"
            "合同期限：5 年\n"
            "年度合同额：约 2.8 亿元\n"
            "团队规模：1,200 人（含配送和安装团队）"
        ),
        "tags": ["家电", "仓配一体", "全国", "大件物流", "安装"],
    },
    {
        "category": "logistics_case",
        "title": "某跨境电商保税仓运营项目",
        "content": (
            "客户：某跨境电商平台\n"
            "项目规模：保税仓 15,000 ㎡（宁波保税区）\n"
            "业务量：日均 30,000 单，SKU 20,000+（美妆/母婴/保健品为主）\n\n"
            "解决方案要点：\n"
            "1. 合规管理：海关三单对碰、保税账册管理\n"
            "2. 存储方案：多温区（常温 + 恒温 25°C），防串味隔离\n"
            "3. 拣选模式：波次拣选 + 播种分拣，效率 200 单/人/小时\n"
            "4. 质检要求：100% 贴中文标签，抽检比例 5%\n"
            "5. 系统对接：海关申报系统 + 平台 OMS + 快递接口\n\n"
            "合同期限：3 年\n"
            "单均操作费：2.8 元/单\n"
            "团队规模：150 人"
        ),
        "tags": ["跨境电商", "保税仓", "海关", "美妆", "母婴"],
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for item in SEED_DATA:
            existing = await db.execute(
                __import__("sqlalchemy").select(KnowledgeEntry)
                .where(KnowledgeEntry.title == item["title"])
            )
            if existing.scalar_one_or_none():
                print(f"  Skip (exists): {item['title']}")
                continue

            entry = KnowledgeEntry(**item)
            db.add(entry)
            print(f"  Added: {item['title']}")

        await db.commit()

    print(f"\nSeeded {len(SEED_DATA)} knowledge entries.")


if __name__ == "__main__":
    print("Seeding knowledge base...")
    asyncio.run(seed())
