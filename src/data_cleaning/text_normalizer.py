from __future__ import annotations

import re


FIELD_ALIASES = {
    "日期": "date",
    "时间": "time",
    "地点": "location",
    "发生时间": "date_time",
    "发生地点": "location",
    "事故类别": "accident_type",
    "事故性质": "accident_type",
    "事故后果": "consequence_text",
    "伤亡情况": "consequence_text",
    "经济损失": "economic_loss_text",
    "事故直接原因": "direct_cause_text",
    "直接原因": "direct_cause_text",
    "间接原因": "indirect_cause_text",
    "事故经过": "process_text",
    "事故原因": "cause_text",
    "改进措施": "measures_text",
    "防范措施": "measures_text",
    "处理措施": "measures_text",
    "单位名称": "organization",
    "严重级别": "severity_level",
}


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_paragraph(paragraph: str) -> str:
    paragraph = paragraph.replace("\u3000", " ")
    paragraph = re.sub(r"\s+", " ", paragraph)
    return paragraph.strip()


def strip_bracket_heading(text: str) -> str:
    return re.sub(r"^【([^】]+)】\s*", "", text).strip()
