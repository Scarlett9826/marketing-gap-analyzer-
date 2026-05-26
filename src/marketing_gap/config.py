"""Configuration loader — reads YAML config + .env file, provides a single Config object."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_dotenv(path: str | Path | None = None) -> dict[str, str]:
    env = {}
    if path is None:
        path = Path.cwd() / ".env"
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


# ── Default dictionaries (used when no YAML override) ──
DEFAULT_OFFICIAL_DICT: dict[str, list[str]] = {
    "大阔折叠形态": ["阔折叠", "大阔折", "√2:1", "1.414", "A4纸", "黄金比例", "黄金阔比例", "阔比例", "岂止于阔"],
    "鸿蒙HarmonyOS6": ["鸿蒙", "HarmonyOS 6", "HarmonyOS6", "原生鸿蒙", "鸿蒙系统", "纯血鸿蒙"],
    "麒麟9030Pro": ["麒麟9030", "麒麟9030 Pro", "麒麟9030Pro"],
    "小艺伴随式AI": ["小艺伴随式", "伴随式AI", "侧拉小艺", "小艺", "AI小艺"],
    "第二代红枫原色": ["红枫", "红枫原色", "二代红枫", "第二代红枫"],
    "RYYB双滤光": ["RYYB", "RYYB传感器", "RYYB双滤光", "双滤光"],
    "超光变主摄": ["超光变", "5000万超光变", "超光变摄像头"],
    "潜望长焦": ["潜望", "潜望式", "潜望长焦", "光学变焦", "100倍数字变焦", "3.5倍光学", "100x", "20x", "增距镜"],
    "十档可变光圈": ["十档", "十档可变光圈", "F1.4-F4.0", "可变光圈", "物理可变光圈"],
    "大内屏7.7英寸": ["7.7英寸", "7.7寸", "内屏", "大内屏"],
    "外屏5.4英寸": ["5.4英寸", "5.4寸", "外屏"],
    "内外屏流转": ["内外屏", "无缝流转", "流转", "屏幕流转"],
    "5050mAh电池": ["5050mAh", "5050 mAh", "5050电池"],
    "100W有线快充": ["100W有线", "100W快充", "100W"],
    "80W无线充电": ["80W无线", "80W"],
    "第二代昆仑玻璃": ["昆仑玻璃", "昆仑", "第二代昆仑"],
    "IPX8防水": ["IPX8", "IPX8防水", "防水"],
    "北斗卫星消息": ["北斗", "卫星消息", "卫星通信"],
    "eSIM支持": ["eSIM", "eSim"],
    "天生会画": ["天生会画"],
    "M-Pen手写笔": ["M-Pen", "手写笔"],
    "120Hz LTPO屏": ["120Hz", "LTPO", "1-120Hz"],
    "229g轻薄": ["229g", "轻薄"],
    "16GB+1TB典藏版": ["16GB", "1TB", "典藏版"],
    "13999元价格": ["13999", "万元", "一万", "11999"],
}

DEFAULT_USER_DICT: dict[str, list[str]] = {
    "大阔折叠形态": ["阔折叠", "大阔折", "阔屏", "宽屏", "1.414", "a4纸", "形态", "比例"],
    "鸿蒙HarmonyOS6": ["鸿蒙", "harmonyos", "鸿蒙系统", "原生鸿蒙", "纯血鸿蒙", "鸿蒙生态"],
    "麒麟9030Pro": ["麒麟", "9030", "国产芯片", "芯片性能", "处理器"],
    "小艺伴随式AI": ["小艺", "伴随式", "ai助手", "侧拉小艺"],
    "第二代红枫原色": ["红枫", "原色"],
    "影像/拍照": ["影像", "拍照", "摄像头", "夜景", "色彩", "样张", "成片", "出片", "拍摄"],
    "潜望长焦": ["长焦", "潜望", "10倍变焦", "20倍变焦", "光学变焦", "100倍", "增距镜", "演唱会"],
    "可变光圈": ["可变光圈", "十档", "光圈"],
    "大内屏7.7英寸": ["7.7", "大屏", "内屏", "看视频", "看片", "刷剧"],
    "外屏宽度85mm": ["85mm", "宽", "宽度", "外屏", "85毫米"],
    "单手操作": ["单手", "单手操作", "够不到", "一只手", "够不着", "拿不住"],
    "内外屏流转": ["流转", "内外屏", "切换", "无缝"],
    "电池续航": ["电池", "续航", "5050", "5300", "电量", "耗电", "充满电", "一天"],
    "100W快充": ["100w", "充电", "快充", "充电速度", "充满"],
    "80W无线充电": ["80w", "无线充", "无线充电"],
    "重量229g": ["229", "重量", "重", "轻", "克", "g", "轻薄", "压手"],
    "厚度": ["厚", "薄", "厚度", "11.2mm", "5.2mm"],
    "屏幕素质": ["屏幕", "亮度", "ltpo", "120hz", "刷新率", "显示", "色准"],
    "折痕": ["折痕", "折痕明显", "中间一道"],
    "折叠耐久": ["耐久", "容易坏", "铰链", "寿命", "怕坏"],
    "应用适配/生态": ["适配", "应用", "app", "生态", "卓易通", "下载不了", "兼容"],
    "信号": ["信号", "卫星", "北斗", "通信"],
    "外观设计": ["外观", "设计", "颜值", "好看", "丑", "活力橙", "星际蓝", "幻夜黑", "零度白"],
    "价格": ["价格", "贵", "便宜", "万元", "一万", "13999", "11999", "性价比", "买不起", "钱"],
    "品牌/华为": ["华为", "余承东", "情怀", "国货"],
    "对比苹果": ["iphone", "苹果", "ios"],
    "对比vivo": ["vivo", "维沃"],
    "对比三星": ["三星", "samsung", "fold", "trifold"],
    "对比mate": ["mate", "matex", "mate70", "mate80"],
    "对比直板机": ["直板", "板砖"],
    "游戏性能": ["王者", "原神", "游戏", "帧率", "卡顿", "发热", "温度"],
    "社交价值/装x": ["装x", "装b", "面子", "牛逼", "高端", "气场", "社交"],
}

DEFAULT_POSITIVE_WORDS = {"好用", "干净", "支持", "站起来", "靠谱", "强", "顶", "丝滑", "纯净", "进步", "可圈可点", "实力", "护城河", "香", "完美", "够用", "不错"}
DEFAULT_NEGATIVE_WORDS = {"翻车", "不行", "拉胯", "劝退", "失望", "差", "慢", "重", "贵", "用不上", "用不到", "没意义", "噱头", "大于实用", "一塌糊涂", "紫边", "没起来", "差距", "限", "中庸"}

DEFAULT_SOURCE_WEIGHTS = {
    "Slogan": 5,
    "产品页文案": 4,
    "发布会现场": 3,
    "深度长文": 3,
    "卖点拆解": 2,
    "预热海报": 2,
    "官方笔记": 2,
    "KOL评测": 2,
    "KOL评测（疑似投放）": 2,
    "媒体转引的疑似Slogan": 2,
    "default": 1,
}


class Config:
    """Unified configuration for a GAP analysis run.

    Loads from:
      1. A YAML config file (product-specific settings)
      2. .env file (secrets)
      3. Built-in defaults (dictionaries, weights)
    """

    def __init__(self, config_path: str | Path, env_path: str | Path | None = None):
        self._raw = {}
        p = Path(config_path)
        if p.exists():
            self._raw = load_yaml(config_path)
        self._env = load_dotenv(env_path)

        config_dir = p.resolve().parent
        self.project_dir = config_dir.parent

        paths = self._raw.get("paths", {})
        self.raw_official = self._resolve(config_dir, paths.get("raw_official", ""))
        self.raw_user = self._resolve(config_dir, paths.get("raw_user", ""))
        self.outputs = self._resolve(config_dir, paths.get("outputs", ""))

    def _resolve(self, base: Path, path: str) -> Path | None:
        if not path:
            return None
        p = Path(path)
        if p.is_absolute():
            return p
        resolved = (base / p).resolve()
        return resolved

    # ── Project info ──
    @property
    def project_name(self) -> str:
        return self._raw.get("project", {}).get("name", "未命名产品")

    @property
    def product_description(self) -> str:
        return self._raw.get("project", {}).get("description", "")

    @property
    def data_date(self) -> str:
        return self._raw.get("project", {}).get("data_date", "")

    # ── Thresholds ──
    @property
    def threshold_official_high(self) -> int:
        return int(self._raw.get("thresholds", {}).get("OFFICIAL_HIGH_THRESHOLD", 5))

    @property
    def threshold_user_high_mention(self) -> int:
        return int(self._raw.get("thresholds", {}).get("USER_HIGH_MENTION_THRESHOLD", 4))

    @property
    def threshold_sentiment_negative(self) -> float:
        return float(self._raw.get("thresholds", {}).get("SENTIMENT_NEGATIVE_THRESHOLD", -0.2))

    @property
    def threshold_sentiment_positive(self) -> float:
        return float(self._raw.get("thresholds", {}).get("SENTIMENT_POSITIVE_THRESHOLD", 0.1))

    # ── Source weights ──
    @property
    def source_weights(self) -> dict[str, int]:
        yaml_weights = self._raw.get("official", {}).get("source_weights", {})
        merged = dict(DEFAULT_SOURCE_WEIGHTS)
        merged.update(yaml_weights)
        return merged

    # ── Dictionaries ──
    @property
    def official_dict(self) -> dict[str, list[str]]:
        return dict(DEFAULT_OFFICIAL_DICT)

    @property
    def user_dict(self) -> dict[str, list[str]]:
        return dict(DEFAULT_USER_DICT)

    @property
    def positive_words(self) -> set[str]:
        return set(DEFAULT_POSITIVE_WORDS)

    @property
    def negative_words(self) -> set[str]:
        return set(DEFAULT_NEGATIVE_WORDS)

    # ── Secrets (from .env) ──
    @property
    def deepseek_api_key(self) -> str:
        return self._env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")

    @property
    def llm_base_url(self) -> str:
        return self._env.get("LLM_BASE_URL") or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")

    @property
    def llm_model(self) -> str:
        return self._env.get("LLM_MODEL") or os.environ.get("LLM_MODEL", "deepseek-chat")
