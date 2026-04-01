# Base Schema

这套仓库默认把数据写入一张飞书 Base 表。最小可运行字段如下。

## 必需字段

### 情报记录

- `标题`：text
- `记录类型`：select
  - `内容发布`
  - `自动情报`
  - `周报`
- `来源平台`：select
  - `Web`
  - `Reddit`
  - `Newsletter`
  - `Forum`
  - `Social`
  - `其他`
  - `选题`
- `来源链接`：text，建议 style 设为 `url`
- `来源账号/网站`：text
- `采集时间`：datetime
- `情报关键词`：text
- `情报摘要`：text
- `情报评分`：number
- `是否转选题`：select
  - `待判断`
  - `已选中`
  - `已忽略`

### 周报记录

- `周报正文`：text

## 推荐视图

### `自动情报采集`

筛选：

```json
{
  "logic": "and",
  "conditions": [
    ["记录类型", "intersects", ["自动情报"]]
  ]
}
```

### `自动情报周报`

筛选：

```json
{
  "logic": "and",
  "conditions": [
    ["记录类型", "intersects", ["周报"]]
  ]
}
```

## 当前脚本如何用这些字段

- `collect_intel_v1.py`
  - 写入网页/RSS 原始情报
- `generate_weekly_topic_packet.py`
  - 从 `自动情报采集` 视图读取原始情报
- `publish_weekly_report_to_base.py`
  - 写入 `记录类型=周报`
- `write_topics_from_editorial_report.py`
  - 从周报中提炼选题，写入 `记录类型=自动情报` 且 `来源平台=选题`

## 分享给别人时的建议

如果别人没有现成的 `Content Calendar`，更适合：

1. 新建一个专用 Base
2. 只按这份 schema 建最小字段
3. 跑通后再自己扩展你们团队原有的内容运营字段
