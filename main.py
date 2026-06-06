import random
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


WOOD_SOUNDS = [
    "咚——！",
    "笃！",
    "哒！咚！",
    "啪嗒！",
    "乓！",
    "叩——",
]

MERIT_LINES = [
    "功德 +1，离成佛又近了一步",
    "善哉善哉，施主今日积德不少",
    "佛祖收到了一条点赞通知",
    "少林寺住持发来贺电",
    "方丈说你这木鱼敲得挺有节奏感",
    "一花一世界，一木一浮生...多敲几下？",
    "木鱼：能不能换个人敲我？",
    "今日功德池已满，溢出部分算明天",
    "阿弥陀佛，功德无量（棒读",
    "你的虔诚把服务器都敲卡了",
]

MILESTONE_LINES = {
    10: "功德十连击！入门级善人！",
    50: "五十大关！你已经从木鱼敲成了铁鱼！",
    100: "功德破百！获得称号：赛博高僧！",
    500: "五百功德！诺贝尔和平奖正在路上...",
    1000: "千锤百炼！这木鱼怕是已经被你敲碎了...",
    10000: "万德归一！你已超越众生于三界之外！",
}

RECALL_SNIFF_LINES = [
    "嗅到了撤回的气息... {name} 刚刚撤回了：\n{content}",
    "撤回也没用！我看到了！{name}：\n{content}",
    "别想逃～ {name} 刚才说：\n{content}",
    "已截图（不是）。{name} 撤回了：\n{content}",
    "撤回记录仪启动！{name}：\n{content}",
]


class Main(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self._last_messages: dict[str, dict] = {}
        self.muyu_enabled = self.config.get("muyu_enabled", True)
        self.recall_sniff_enabled = self.config.get("recall_sniff_enabled", True)
        self._recall_hooked = False
        logger.info("[muyu] 赛博木鱼 + 撤回嗅探已就位，咚——")

    # ==================== 木鱼 ====================

    async def _get_merits(self) -> dict:
        return await self.get_kv_data("merits", {})

    async def _save_merits(self, data: dict):
        await self.put_kv_data("merits", data)

    async def _get_group_merits(self, group_id: str) -> dict:
        merits = await self._get_merits()
        return merits.get(group_id, {})

    async def _add_merit(self, group_id: str, user_id: str):
        merits = await self._get_merits()
        group = merits.setdefault(group_id, {})
        group[user_id] = group.get(user_id, 0) + 1
        await self._save_merits(merits)
        return group[user_id]

    async def _get_leaderboard(self, group_id: str):
        group = await self._get_group_merits(group_id)
        board = sorted(group.items(), key=lambda x: x[1], reverse=True)
        return board[:10]

    @filter.command("敲木鱼")
    async def muyu(self, event: AstrMessageEvent):
        """敲一下赛博木鱼，功德 +1"""
        if not self.muyu_enabled:
            return
        group_id = event.get_group_id() or "private"
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        count = await self._add_merit(group_id, user_id)

        sound = random.choice(WOOD_SOUNDS)
        line = random.choice(MERIT_LINES)
        msg = f"{sound}\n{user_name} 功德 +1（累计 {count}）\n{line}"

        if count in MILESTONE_LINES:
            msg += f"\n\n{MILESTONE_LINES[count]}"

        yield event.plain_result(msg)

    @filter.command("功德排行榜")
    async def leaderboard(self, event: AstrMessageEvent):
        """功德排行榜 Top 10"""
        group_id = event.get_group_id() or "private"
        board = await self._get_leaderboard(group_id)

        if not board:
            yield event.plain_result("功德榜空空如也，还没人敲过木鱼呢～")
            return

        lines = ["===  功德排行榜  ===", ""]
        medals = ["[1]", "[2]", "[3]"]
        for i, (uid, count) in enumerate(board):
            prefix = medals[i] if i < 3 else f" {i+1}."
            lines.append(f"  {prefix} {uid}: {count} 功德")

        total = sum(c for _, c in board)
        lines.append("")
        lines.append(f"全群总计: {total} 功德")

        yield event.plain_result("\n".join(lines))

    @filter.command("今日功德")
    async def my_merit(self, event: AstrMessageEvent):
        """查看自己的功德数"""
        group_id = event.get_group_id() or "private"
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        group = await self._get_group_merits(group_id)
        count = group.get(user_id, 0)

        if count == 0:
            yield event.plain_result(f"{user_name} 今日尚未敲过木鱼，善哉～")
        else:
            yield event.plain_result(f"{user_name} 今日功德: {count}")

    # ==================== 撤回嗅探 ====================

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def _cache_message(self, event: AstrMessageEvent):
        """缓存每条群消息，供撤回时复读"""
        if not self.recall_sniff_enabled:
            return
        msg_id = event.message_obj.message_id
        user_name = event.get_sender_name()
        content = event.message_str.strip()
        if msg_id and content:
            self._last_messages[msg_id] = {
                "name": user_name,
                "content": content,
            }
            # 只保留最近 200 条
            if len(self._last_messages) > 200:
                oldest = next(iter(self._last_messages))
                del self._last_messages[oldest]

    @filter.on_astrbot_loaded()
    async def _hook_recall(self):
        """在 AstrBot 加载完成后，向 aiocqhttp 平台注册撤回监听"""
        if self._recall_hooked or not self.recall_sniff_enabled:
            return
        self._recall_hooked = True

        platforms = self.context.platform_manager.get_insts()
        for plat in platforms:
            meta = plat.meta()
            if meta.name != "aiocqhttp":
                continue

            try:
                client = plat.get_client()
            except Exception:
                continue

            @client.on_notice("group_recall")
            async def _on_group_recall(event):
                msg_id = str(event.get("message_id", ""))
                group_id = str(event.get("group_id", ""))
                user_id = str(event.get("user_id", ""))

                if msg_id not in self._last_messages:
                    return

                cached = self._last_messages.pop(msg_id)
                name = cached["name"]
                content = cached["content"]
                line = random.choice(RECALL_SNIFF_LINES).format(name=name, content=content)

                try:
                    await client.api.send_group_msg(
                        group_id=group_id,
                        message=line,
                    )
                except Exception as e:
                    logger.error(f"[muyu] 撤回复读失败: {e}")

            logger.info(f"[muyu] 撤回嗅探已绑定到 {meta.name}")
