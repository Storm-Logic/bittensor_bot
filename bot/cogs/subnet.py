"""
bot/cogs/subnet.py

Discord cog — handles @mentions, DMs, and slash commands.
"""

from __future__ import annotations

import re
import logging

import discord
from discord.ext import commands, tasks

from data.fetcher import build_live_data_block, get_uid_info
from data.wandb_service import wandb_cache
from data.knowledge_store import get_links
from rag.pipeline import retrieve, index_docs
from bot.claude_handler import ask_claude
from config.settings import ALLOWED_CHANNEL_IDS

logger = logging.getLogger(__name__)

LIVE_DATA_TRIGGERS = {
    "price", "alpha", "liquidity", "pool", "miner", "uid", "rank",
    "score", "stake", "top", "validator", "emission", "tempo", "neuron",
    "subnet", "stats",
}

def _needs_live(query: str) -> bool:
    return bool(LIVE_DATA_TRIGGERS & set(query.lower().split()))

def _extract_uid(query: str):
    m = re.search(r'\buid\s*#?(\d+)\b', query.lower())
    return int(m.group(1)) if m else None


class SubnetCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reindex.start()

    def cog_unload(self):
        self._reindex.cancel()

    # ── Auto re-index docs every 6h ───────────────────────────────────────────

    @tasks.loop(hours=6)
    async def _reindex(self):
        logger.info("Scheduled doc re-index...")
        try:
            index_docs()
        except Exception as e:
            logger.error(f"Re-index error: {e}")

    @_reindex.before_loop
    async def _before_reindex(self):
        await self.bot.wait_until_ready()

    # ── Message handler ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
            return

        is_mention = self.bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        if not (is_mention or is_dm):
            return

        query = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
        if not query:
            await message.reply("Hey! Ask me anything about the subnet.")
            return

        async with message.channel.typing():
            chain_data = ""
            wandb_data = ""

            uid = _extract_uid(query)
            if uid is not None:
                # Merge chain + wandb info for this specific UID
                chain = get_uid_info(uid)
                wb    = wandb_cache.get_uid_info(uid)
                parts = []
                if chain and "error" not in chain:
                    parts.append("Chain: " + ", ".join(f"{k}={v}" for k, v in chain.items()))
                if wb:
                    parts.append(
                        f"WandB: rank={wb['rank']}, avg_score={wb['avg_score']}, "
                        f"last_score={wb['last_score']}, records={wb['records']}, "
                        f"recent_scores={wb['recent_scores']}"
                    )
                chain_data = "\n".join(parts) if parts else f"No data found for UID {uid}"
            elif _needs_live(query):
                chain_data = build_live_data_block()
                wandb_data = wandb_cache.get_summary_block()

            rag_context = retrieve(query)
            answer = await ask_claude(query, chain_data, wandb_data, rag_context)

        await message.reply(answer)

    # ── Slash commands ────────────────────────────────────────────────────────

    @discord.app_commands.command(name="uid", description="Get chain + wandb info for a miner UID")
    async def cmd_uid(self, interaction: discord.Interaction, uid: int):
        await interaction.response.defer()
        chain = get_uid_info(uid)
        wb    = wandb_cache.get_uid_info(uid)

        embed = discord.Embed(title=f"UID {uid}", color=0x00d4aa)

        if chain and "error" not in chain:
            embed.add_field(name="Chain rank",  value=str(chain.get("chain_rank", "N/A")), inline=True)
            embed.add_field(name="Chain score", value=str(chain.get("chain_score", "N/A")), inline=True)
            embed.add_field(name="Stake",       value=str(chain.get("stake", "N/A")),       inline=True)
        elif chain and "error" in chain:
            embed.add_field(name="Chain", value=chain["error"], inline=False)

        if wb:
            embed.add_field(name="WandB rank",  value=str(wb["rank"]),       inline=True)
            embed.add_field(name="Avg score",   value=str(wb["avg_score"]),  inline=True)
            embed.add_field(name="Last score",  value=str(wb["last_score"]), inline=True)
            recent = " | ".join(str(s) for s in wb["recent_scores"][-5:])
            embed.add_field(name="Recent scores (last 5)", value=recent, inline=False)
        else:
            embed.add_field(name="WandB", value="No data yet", inline=False)

        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name="top", description="Show top miners from wandb")
    async def cmd_top(self, interaction: discord.Interaction):
        await interaction.response.defer()
        miners = wandb_cache.get_top_miners(10)
        if not miners:
            await interaction.followup.send("No miner data yet — wandb poller is still warming up.")
            return
        embed = discord.Embed(title="Top 10 Miners", color=0x00d4aa)
        rows = "\n".join(
            f"#{m['rank']:>2}  UID {m['uid']:<5}  avg={m['avg_score']}  last={m['last_score']}  n={m['records']}"
            for m in miners
        )
        embed.description = f"```\n{rows}\n```"
        embed.set_footer(text=f"Updated: {wandb_cache.last_updated or 'pending'} | Runs: {', '.join(wandb_cache.active_run_ids)}")
        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name="subnet", description="Show live subnet stats")
    async def cmd_subnet(self, interaction: discord.Interaction):
        await interaction.response.defer()
        chain = build_live_data_block()
        wb    = wandb_cache.get_summary_block()
        embed = discord.Embed(title="Subnet Stats", color=0xff9900)
        embed.description = f"```\n{chain}\n\n{wb}\n```"
        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name="links", description="Show all reference links")
    async def cmd_links(self, interaction: discord.Interaction):
        links = get_links()
        if not links:
            await interaction.response.send_message("No reference links configured yet.")
            return
        embed = discord.Embed(title="Reference Links", color=0x0099ff)
        for l in links:
            label = l.get("description") or l["url"]
            embed.add_field(name=l["label"], value=f"[{label}]({l['url']})", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="reindex", description="[Admin] Re-index docs from GitHub")
    @commands.has_permissions(administrator=True)
    async def cmd_reindex(self, interaction: discord.Interaction):
        await interaction.response.send_message("Re-indexing docs from GitHub...")
        try:
            index_docs()
            await interaction.followup.send("Done — docs re-indexed.")
        except Exception as e:
            await interaction.followup.send(f"Failed: {e}")


async def setup(bot: commands.Bot):
    cog = SubnetCog(bot)
    await bot.add_cog(cog)
    await bot.tree.sync()
