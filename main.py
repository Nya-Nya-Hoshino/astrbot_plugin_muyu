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


class Main(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        logger.info("[muyu] 赛博木鱼已就位，咚——")

    async def _get_merit(self, group_id: str, user_id: str) -> int:
        key = f"merit_{group_id}_{user_id}"
        val = await self.plugin_kv_store.get(key)
        return int(val) if val else 0

    async def _set_merit(self, group_id: str, user_id: str, count: int):
        key = f"merit_{group_id}_{user_id}"
        await self.plugin_kv_store.set(key, str(count))

    async def _get_leaderboard(self, group_id: str):
        prefix = f"merit_{group_id}_"
        all_keys = await self.plugin_kv_store.keys()
        board = []
        for k in all_keys:
            if k.startswith(prefix):
                uid = k[len(prefix):]
                val = await self.plugin_kv_store.get(k)
                if val:
                    board.append((uid, int(val)))
        board.sort(key=lambda x: x[1], reverse=True)
        return board[:10]

    @filter.command("敲木鱼")
    async def muyu(self, event: AstrMessageEvent):
        """敲一下赛博木鱼，功德 +1"""
        group_id = event.get_group_id() or "private"
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        count = await self._get_merit(group_id, user_id)
        count += 1
        await self._set_merit(group_id, user_id, count)

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
        count = await self._get_merit(group_id, user_id)

        if count == 0:
            yield event.plain_result(f"{user_name} 今日尚未敲过木鱼，善哉～")
        else:
            yield event.plain_result(f"{user_name} 今日功德: {count}")
