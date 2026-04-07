"""Project templates API — pre-configured industry templates."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user

router = APIRouter(prefix="/templates", tags=["templates"])


class ProjectTemplate(BaseModel):
    id: str
    name: str
    industry: str
    description: str
    icon: str
    assumptions: dict


TEMPLATES: list[ProjectTemplate] = [
    ProjectTemplate(
        id="ecommerce_warehouse",
        name="电商仓储物流",
        industry="电商",
        icon="📦",
        description="B2C 电商订单履行仓库，高频次、多SKU、快速出库",
        assumptions={
            "warehouse_type": "电商履行仓",
            "temperature": "常温",
            "daily_order_range": "5,000-50,000 单",
            "sku_range": "10,000-100,000",
            "peak_factor": 3.0,
            "sla_same_day_rate": "95%",
            "sla_accuracy": "99.9%",
            "automation_level": "中等（AGV/输送线）",
            "shift_model": "2班制",
            "typical_area_sqm": "10,000-50,000",
            "typical_contract_years": 3,
        },
    ),
    ProjectTemplate(
        id="cold_chain",
        name="冷链仓储",
        industry="冷链",
        icon="❄️",
        description="温控仓储（冷藏/冷冻），适用于食品、医药、生鲜",
        assumptions={
            "warehouse_type": "冷链仓",
            "temperature_zones": ["-18°C 冷冻", "0-4°C 冷藏", "15-25°C 恒温"],
            "daily_order_range": "1,000-10,000 单",
            "sku_range": "1,000-10,000",
            "sla_temperature_compliance": "100%",
            "sla_accuracy": "99.95%",
            "certifications": ["HACCP", "ISO22000", "GSP（医药）"],
            "automation_level": "中高（减少人员在冷区作业时间）",
            "typical_area_sqm": "5,000-20,000",
            "energy_cost_factor": 3.0,
            "typical_contract_years": 5,
        },
    ),
    ProjectTemplate(
        id="auto_parts",
        name="汽车售后备件仓储",
        industry="汽车",
        icon="🚗",
        description="汽车售后备件仓库，多规格、长尾SKU、高准确率要求",
        assumptions={
            "warehouse_type": "汽车备件仓",
            "temperature": "常温（部分恒温）",
            "daily_order_range": "500-5,000 单",
            "sku_range": "30,000-200,000",
            "sku_characteristics": "长尾分布，大小件混合，部分超大件",
            "sla_order_leadtime": "4小时（紧急件）/ 24小时（常规件）",
            "sla_accuracy": "99.98%",
            "storage_types": ["货架（小件）", "地堆（大件）", "立体库（高频件）"],
            "automation_level": "中等（PTL + 输送线）",
            "traceability": "全程追溯（VIN码/零件号）",
            "typical_area_sqm": "10,000-30,000",
            "typical_contract_years": 5,
        },
    ),
    ProjectTemplate(
        id="pharma",
        name="医药物流仓储",
        industry="医药",
        icon="💊",
        description="GSP合规的医药仓储，严格温控和追溯要求",
        assumptions={
            "warehouse_type": "医药仓",
            "temperature_zones": ["2-8°C 冷藏", "15-25°C 阴凉", "常温"],
            "daily_order_range": "1,000-8,000 单",
            "sku_range": "5,000-30,000",
            "certifications": ["GSP", "GMP", "ISO9001"],
            "sla_accuracy": "99.99%",
            "regulatory": ["药品电子监管码", "批号追溯", "效期管理（近效期预警）"],
            "automation_level": "高（AS/RS + 自动分拣，减少人工触碰）",
            "typical_area_sqm": "5,000-15,000",
            "typical_contract_years": 5,
        },
    ),
    ProjectTemplate(
        id="fmcg",
        name="快消品分拨中心",
        industry="快消",
        icon="🏪",
        description="快消品区域分拨中心，大批量、高周转、门店配送",
        assumptions={
            "warehouse_type": "分拨中心/DC",
            "temperature": "常温（部分恒温区）",
            "daily_throughput": "100,000-500,000 件",
            "sku_range": "3,000-15,000",
            "delivery_model": "城市配送 + 末端门店",
            "sla_delivery": "T+1 次日达",
            "sla_accuracy": "99.95%",
            "automation_level": "高（交叉带分拣 + 输送线）",
            "typical_area_sqm": "15,000-50,000",
            "typical_contract_years": 3,
        },
    ),
    ProjectTemplate(
        id="manufacturing",
        name="制造业供应链仓储",
        industry="制造",
        icon="🏭",
        description="制造业原材料/成品仓储，VMI/JIT 模式",
        assumptions={
            "warehouse_type": "原材料仓 + 成品仓",
            "temperature": "常温",
            "daily_throughput": "500-5,000 托盘",
            "sku_range": "5,000-30,000",
            "supply_model": "VMI / JIT / 安全库存",
            "storage_types": ["托盘货架", "驶入式货架", "悬臂架（长条件）"],
            "sla_delivery": "按生产计划准时配送",
            "sla_accuracy": "99.95%",
            "automation_level": "中等（AGV + WMS 集成 ERP）",
            "typical_area_sqm": "10,000-40,000",
            "typical_contract_years": 5,
        },
    ),
]


@router.get("", response_model=list[ProjectTemplate])
async def list_templates(user: dict = Depends(get_current_user)):
    """List all available project templates."""
    return TEMPLATES


@router.get("/{template_id}", response_model=ProjectTemplate)
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    """Get a specific template by ID."""
    for t in TEMPLATES:
        if t.id == template_id:
            return t
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Template not found")
