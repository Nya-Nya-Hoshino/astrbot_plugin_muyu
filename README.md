# astrbot-plugin-muyu

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![AstrBot](https://img.shields.io/badge/AstrBot-plugin-6c5ce7.svg)](https://github.com/AstrBotDevs/AstrBot)

赛博木鱼 + 撤回嗅探 —— 群聊快乐源泉二合一。

## 功能

### 赛博木鱼

敲一下功德 +1，攒排名冲里程碑，解压神器。

| 指令 | 说明 |
|------|------|
| `/敲木鱼` | 敲一下，功德 +1，随机趣评 |
| `/功德排行榜` | 查看群内功德 Top 10 |
| `/今日功德` | 查看自己的功德数 |

**里程碑成就**：10（入门善人）→ 50（铁鱼）→ 100（赛博高僧）→ 500（诺贝尔候补）→ 1000（木鱼已碎）→ 10000（超越三界）

### 撤回嗅探

群聊有人撤回消息？bot 当场复读，让撤回无所遁形。

- 自动缓存最近 200 条群消息
- 检测到撤回时，复读撤回内容 + 发送者名字
- 仅群聊生效，私聊不受影响

## 安装

```bash
cd ~/.astrbot/data/plugins
git clone https://github.com/Nya-Nya-Hoshino/astrbot_plugin_muyu.git muyu
```

## 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| muyu_enabled | bool | true | 启用赛博木鱼 |
| recall_sniff_enabled | bool | true | 启用撤回嗅探 |

## 技术实现

- 木鱼数据使用 `plugin_kv_store` 按群隔离持久化
- 撤回监听通过 `on_astrbot_loaded` 钩子注入 aiocqhttp 的 `on_notice('group_recall')` 事件

## 许可证

MIT License
