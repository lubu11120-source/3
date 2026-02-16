import discord
from discord.ext import tasks
import json
import os
from datetime import datetime, timedelta
import pytz

# ── Configuration ────────────────────────────────────────────────
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # Railway liest aus Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # Railway liest aus Environment Variables
POINTS_FILE = "points.json"
SUBMISSIONS_FILE = "submissions.json"
ADMIN_ROLE_NAME = "leadership teammember"
TASK_CHANNEL_NAME = "task-creation"
OPEN_TASKS_CHANNEL_NAME = "open-tasks"
CLAIM_CHANNEL_NAME = "claim-points"
APPROVAL_CHANNEL_NAME = "task-approval"
WEEKLY_CHANNEL_NAME = "weakly-leaderboard"
MONTHLY_CHANNEL_NAME = "monthly-leaderboard"
TIMEZONE = pytz.timezone("Europe/Berlin")


# ── File Helpers ─────────────────────────────────────────────────
def load_tasks() -> dict:
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tasks(tasks: dict) -> None:
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def load_points() -> dict:
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"weekly": {}, "monthly": {}}

def save_points(points: dict) -> None:
    os.makedirs(os.path.dirname(POINTS_FILE), exist_ok=True)
    with open(POINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=2)

def load_submissions() -> dict:
    if os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_submissions(submissions: dict) -> None:
    os.makedirs(os.path.dirname(SUBMISSIONS_FILE), exist_ok=True)
    with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(submissions, f, ensure_ascii=False, indent=2)

def has_admin_role(interaction: discord.Interaction) -> bool:
    role = discord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
    return role is not None and role in interaction.user.roles

def ensure_points_structure(points: dict) -> dict:
    if "weekly" not in points:
        points["weekly"] = {}
    if "monthly" not in points:
        points["monthly"] = {}
    return points


# ── Bot ──────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)


# ── Leaderboard Helpers ───────────────────────────────────────────
def build_leaderboard_embed(
    guild: discord.Guild,
    period: str,
    points_data: dict,
    title: str,
    color: discord.Color,
    footer: str = "",
) -> discord.Embed:
    bucket = points_data.get(period, {})
    sorted_members = sorted(
        [(mid, data) for mid, data in bucket.items()],
        key=lambda x: x[1].get("total_points", 0),
        reverse=True,
    )
    embed = discord.Embed(title=title, color=color)
    if not sorted_members or all(d.get("total_points", 0) == 0 for _, d in sorted_members):
        embed.description = "*No points have been awarded yet.*"
    else:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        rank = 1
        for member_id, data in sorted_members:
            pts = data.get("total_points", 0)
            if pts == 0:
                continue
            member = guild.get_member(int(member_id))
            name   = member.display_name if member else f"User {member_id}"
            icon   = medals.get(rank, f"**#{rank}**")
            lines.append(f"{icon} {name} — **{pts} pts**")
            rank += 1
        embed.description = "\n".join(lines) if lines else "*No points have been awarded yet.*"
    if footer:
        embed.set_footer(text=footer)
    return embed


async def update_leaderboard_channel(guild: discord.Guild, period: str):
    channel_name = WEEKLY_CHANNEL_NAME if period == "weekly" else MONTHLY_CHANNEL_NAME
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        return
    points_data = load_points()
    now_local   = datetime.now(TIMEZONE)
    if period == "weekly":
        title  = "📅 Weekly Leaderboard"
        color  = discord.Color.blue()
        footer = f"Resets every Monday at 19:00 · Last updated: {now_local.strftime('%d.%m.%Y %H:%M')}"
    else:
        title  = "🗓️ Monthly Leaderboard"
        color  = discord.Color.purple()
        footer = f"Resets on the 1st of each month at 20:00 · Last updated: {now_local.strftime('%d.%m.%Y %H:%M')}"
    embed = build_leaderboard_embed(guild, period, points_data, title, color, footer)
    live_msg = None
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            if msg.embeds[0].title and "FINAL STANDINGS" not in msg.embeds[0].title:
                live_msg = msg
                break
    if live_msg:
        await live_msg.edit(embed=embed)
    else:
        await channel.send(embed=embed)


async def reset_leaderboard(guild: discord.Guild, period: str):
    channel_name = WEEKLY_CHANNEL_NAME if period == "weekly" else MONTHLY_CHANNEL_NAME
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        return
    points_data = load_points()
    now_local   = datetime.now(TIMEZONE)
    if period == "weekly":
        snapshot_title = f"📅 FINAL STANDINGS — Week ending {now_local.strftime('%d.%m.%Y')}"
        color          = discord.Color.blue()
    else:
        snapshot_title = f"🗓️ FINAL STANDINGS — {now_local.strftime('%B %Y')}"
        color          = discord.Color.purple()
    snapshot_embed = build_leaderboard_embed(
        guild, period, points_data,
        title  = snapshot_title,
        color  = color,
        footer = f"Archived on {now_local.strftime('%d.%m.%Y at %H:%M')}",
    )
    await channel.send(embed=snapshot_embed)
    for member_id in points_data.get(period, {}):
        points_data[period][member_id]["total_points"] = 0
        points_data[period][member_id]["completions"]  = {}
    save_points(points_data)
    await update_leaderboard_channel(guild, period)


# ── Scheduled Resets ──────────────────────────────────────────────
@tasks.loop(minutes=1)
async def check_resets():
    now = datetime.now(TIMEZONE)
    is_weekly_reset  = (now.weekday() == 0 and now.hour == 19 and now.minute == 0)
    is_monthly_reset = (now.day == 1      and now.hour == 20 and now.minute == 0)
    for guild in bot.guilds:
        if is_weekly_reset:
            await reset_leaderboard(guild, "weekly")
        if is_monthly_reset:
            await reset_leaderboard(guild, "monthly")


# ── Remove Buttons from Old Messages ─────────────────────────────
async def disable_old_control_messages(channel: discord.TextChannel):
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.components:
            try:
                await msg.edit(view=discord.ui.View())
            except discord.NotFound:
                pass


# ── Update #open-tasks ────────────────────────────────────────────
async def update_open_tasks_channel(guild: discord.Guild):
    channel = discord.utils.get(guild.text_channels, name=OPEN_TASKS_CHANNEL_NAME)
    if not channel:
        return
    async for msg in channel.history(limit=100):
        if msg.author == bot.user:
            try:
                await msg.delete()
            except discord.NotFound:
                pass
    tasks = load_tasks()
    embed = discord.Embed(title="📋 Open Orders", color=discord.Color.gold())
    if tasks:
        for task in tasks.values():
            max_display = "Unlimited" if task["max_completions"] == 0 else f"{task['max_completions']}x"
            embed.add_field(
                name=f"📌 {task['name']}",
                value=f"⭐ **{task['points']} Points** | 🔄 Max. **{max_display}**",
                inline=False,
            )
    else:
        embed.description = "*No open orders at the moment.*"
    await channel.send(embed=embed)


# ── Send Control Message (#task-creation) ────────────────────────
async def send_control_message(channel: discord.TextChannel):
    await disable_old_control_messages(channel)
    tasks = load_tasks()
    embed = discord.Embed(title="📋 Order Management", color=discord.Color.blurple())
    if tasks:
        for task in tasks.values():
            max_display = "Unlimited" if task["max_completions"] == 0 else f"{task['max_completions']}x"
            embed.add_field(
                name=f"📌 {task['name']}",
                value=f"⭐ **{task['points']} Points** | 🔄 Max. **{max_display}**",
                inline=False,
            )
    else:
        embed.description = "*No orders created yet.*"
    await channel.send(embed=embed, view=TaskControlView())


# ── Send Submit Button (#claim-points) ───────────────────────────
async def send_claim_message(channel: discord.TextChannel):
    await disable_old_control_messages(channel)
    embed = discord.Embed(
        title="🏆 Claim Points",
        description="Completed a task? Click **Submit Task** to log your points!",
        color=discord.Color.green(),
    )
    await channel.send(embed=embed, view=ClaimControlView())


# ── Build Submission Embed ────────────────────────────────────────
def build_submission_embed(
    member: discord.Member,
    task: dict,
    amount: int,
    earned_points: int,
    weekly_total: int,
    monthly_total: int,
    status: str,
) -> discord.Embed:
    if status == "approved":
        color      = discord.Color.green()
        status_str = "✅ **APPROVED**"
    elif status == "rejected":
        color      = discord.Color.red()
        status_str = "❌ **NOT APPROVED**"
    else:
        color      = discord.Color.orange()
        status_str = "🕐 **PENDING**"
    embed = discord.Embed(title="🏆 Task Submission", color=color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Member",                value=member.mention,             inline=True)
    embed.add_field(name="📌 Task",                  value=task["name"],               inline=True)
    embed.add_field(name="🔄 Submissions",           value=f"{amount}x",               inline=True)
    embed.add_field(name="⭐ Points per Completion", value=f"{task['points']} pts",    inline=True)
    embed.add_field(name="💰 Points Earned",         value=f"**{earned_points} pts**", inline=True)
    embed.add_field(name="\u200b",                   value="\u200b",                  inline=True)
    embed.add_field(name="📅 Weekly Total",          value=f"**{weekly_total} pts**",  inline=True)
    embed.add_field(name="🗓️ Monthly Total",        value=f"**{monthly_total} pts**", inline=True)
    embed.add_field(name="📋 Status",                value=status_str,                inline=False)
    max_display = "Unlimited" if task["max_completions"] == 0 else f"{task['max_completions']}x"
    embed.set_footer(text=f"Max completions for this task: {max_display}")
    return embed


# ── Approval View ─────────────────────────────────────────────────
class ApprovalView(discord.ui.View):
    def __init__(self, submission_id: str):
        super().__init__(timeout=None)
        self.submission_id = submission_id

    @discord.ui.button(label="Approved", style=discord.ButtonStyle.green, emoji="✅", custom_id="btn_approve")
    async def approve(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not has_admin_role(interaction):
            await interaction.response.send_message(f"🚫 You need the **{ADMIN_ROLE_NAME}** role.", ephemeral=True)
            return
        await self._resolve(interaction, "approved")

    @discord.ui.button(label="Not Approved", style=discord.ButtonStyle.red, emoji="❌", custom_id="btn_reject")
    async def reject(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not has_admin_role(interaction):
            await interaction.response.send_message(f"🚫 You need the **{ADMIN_ROLE_NAME}** role.", ephemeral=True)
            return
        await self._resolve(interaction, "rejected")

    async def _resolve(self, interaction: discord.Interaction, status: str):
        submissions = load_submissions()
        sub = submissions.get(self.submission_id)
        if not sub:
            await interaction.response.send_message("⚠️ Submission not found.", ephemeral=True)
            return
        if sub["status"] != "pending":
            await interaction.response.send_message("⚠️ Already reviewed.", ephemeral=True)
            return
        points_data = ensure_points_structure(load_points())
        member_id   = sub["member_id"]
        task        = sub["task"]
        task_key    = sub["task_key"]
        amount      = sub["amount"]
        earned      = sub["earned_points"]
        if status == "approved":
            for period in ("weekly", "monthly"):
                if member_id not in points_data[period]:
                    points_data[period][member_id] = {"total_points": 0, "completions": {}}
                points_data[period][member_id]["total_points"] += earned
                prev = points_data[period][member_id]["completions"].get(task_key, 0)
                points_data[period][member_id]["completions"][task_key] = prev + amount
        else:
            for period in ("weekly", "monthly"):
                if member_id in points_data.get(period, {}):
                    prev = points_data[period][member_id]["completions"].get(task_key, 0)
                    points_data[period][member_id]["completions"][task_key] = max(0, prev - amount)
        save_points(points_data)
        weekly_total  = points_data["weekly"].get(member_id,  {}).get("total_points", 0)
        monthly_total = points_data["monthly"].get(member_id, {}).get("total_points", 0)
        sub["status"]      = status
        sub["reviewed_by"] = interaction.user.display_name
        submissions[self.submission_id] = sub
        save_submissions(submissions)
        try:
            member = await interaction.guild.fetch_member(int(member_id))
        except discord.NotFound:
            member = interaction.user
        new_embed = build_submission_embed(
            member        = member,
            task          = task,
            amount        = amount,
            earned_points = earned,
            weekly_total  = weekly_total,
            monthly_total = monthly_total,
            status        = status,
        )
        new_embed.set_footer(text=f"Reviewed by {interaction.user.display_name}")
        await interaction.response.edit_message(embed=new_embed, view=discord.ui.View())
        claim_channel = discord.utils.get(interaction.guild.text_channels, name=CLAIM_CHANNEL_NAME)
        if claim_channel and sub.get("claim_message_id"):
            try:
                claim_msg = await claim_channel.fetch_message(int(sub["claim_message_id"]))
                await claim_msg.edit(embed=new_embed)
            except discord.NotFound:
                pass
        if status == "approved":
            await update_leaderboard_channel(interaction.guild, "weekly")
            await update_leaderboard_channel(interaction.guild, "monthly")
        await interaction.followup.send(
            f"{'✅ Approved' if status == 'approved' else '❌ Rejected'} — **{member.display_name}**.",
            ephemeral=True,
        )


# ════════════════════════════════════════════════════════════════
#  CLAIM FLOW
# ════════════════════════════════════════════════════════════════

class ClaimControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit Task", style=discord.ButtonStyle.green, emoji="🏆", custom_id="btn_submit_task")
    async def submit_task(self, button: discord.ui.Button, interaction: discord.Interaction):
        tasks = load_tasks()
        if not tasks:
            await interaction.response.send_message("📭 No open orders available.", ephemeral=True)
            return
        view = TaskSelectView(tasks)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📋 Select a Task",
                description="Choose the task you completed from the dropdown below:",
                color=discord.Color.blurple(),
            ),
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()


class TaskSelectView(discord.ui.View):
    def __init__(self, tasks: dict):
        super().__init__(timeout=300)
        self.add_item(TaskDropdown(tasks))
        self.message = None

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass


class TaskDropdown(discord.ui.Select):
    def __init__(self, tasks: dict):
        self.tasks = tasks
        options = [
            discord.SelectOption(
                label=task["name"],
                value=task_key,
                description=f"{task['points']} pts · Max {task['max_completions'] if task['max_completions'] != 0 else '∞'}x",
                emoji="📌",
            )
            for task_key, task in tasks.items()
        ]
        super().__init__(
            placeholder="Select a task...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="task_select_dropdown",
        )

    async def callback(self, interaction: discord.Interaction):
        selected_key  = self.values[0]
        selected_task = self.tasks[selected_key]
        await interaction.response.send_modal(AmountModal(selected_key, selected_task))
        try:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="📋 Task Selected",
                    description=f"Submission form opened for **{selected_task['name']}**.",
                    color=discord.Color.blurple(),
                ),
                view=discord.ui.View(),
            )
        except discord.NotFound:
            pass


class AmountModal(discord.ui.Modal):
    def __init__(self, task_key: str, task: dict):
        max_label = "unlimited" if task["max_completions"] == 0 else str(task["max_completions"])
        super().__init__(title=f"📌 {task['name']}")
        self.task_key = task_key
        self.task     = task
        self.add_item(discord.ui.InputText(
            label=f"Number of Completions (max: {max_label})",
            placeholder=f"Enter a number (1–{max_label})" if task["max_completions"] != 0 else "Enter a number (e.g. 3)",
            min_length=1,
            max_length=4,
            style=discord.InputTextStyle.short,
        ))

    async def callback(self, interaction: discord.Interaction):
        amount_raw = self.children[0].value.strip()
        task       = self.task
        user       = interaction.user
        try:
            amount = int(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid positive integer.", ephemeral=True)
            return
        points_data = ensure_points_structure(load_points())
        member_id   = str(user.id)
        if task["max_completions"] != 0:
            already_done = points_data["weekly"].get(member_id, {}).get("completions", {}).get(self.task_key, 0)
            remaining    = task["max_completions"] - already_done
            if remaining <= 0:
                await interaction.response.send_message(
                    f"⛔ You've reached the maximum completions (**{task['max_completions']}x**) for **{task['name']}**.",
                    ephemeral=True,
                )
                return
            if amount > remaining:
                await interaction.response.send_message(
                    f"⚠️ You can only submit **{remaining}** more completion(s) for **{task['name']}**.",
                    ephemeral=True,
                )
                return
        earned_points = task["points"] * amount
        for period in ("weekly", "monthly"):
            if member_id not in points_data[period]:
                points_data[period][member_id] = {"total_points": 0, "completions": {}}
            prev = points_data[period][member_id]["completions"].get(self.task_key, 0)
            points_data[period][member_id]["completions"][self.task_key] = prev + amount
        save_points(points_data)
        weekly_total  = points_data["weekly"].get(member_id,  {}).get("total_points", 0)
        monthly_total = points_data["monthly"].get(member_id, {}).get("total_points", 0)
        await interaction.response.send_message("✅ Your submission has been sent for approval!", ephemeral=True)
        claim_channel = discord.utils.get(interaction.guild.text_channels, name=CLAIM_CHANNEL_NAME)
        claim_msg_id  = None
        if claim_channel:
            pending_embed = build_submission_embed(user, task, amount, earned_points, weekly_total, monthly_total, "pending")
            claim_msg     = await claim_channel.send(embed=pending_embed)
            claim_msg_id  = str(claim_msg.id)
            await send_claim_message(claim_channel)
        submission_id    = f"{member_id}_{interaction.id}"
        approval_channel = discord.utils.get(interaction.guild.text_channels, name=APPROVAL_CHANNEL_NAME)
        if approval_channel:
            approval_embed = build_submission_embed(user, task, amount, earned_points, weekly_total, monthly_total, "pending")
            await approval_channel.send(embed=approval_embed, view=ApprovalView(submission_id))
        submissions = load_submissions()
        submissions[submission_id] = {
            "member_id":        member_id,
            "task_key":         self.task_key,
            "task":             task,
            "amount":           amount,
            "earned_points":    earned_points,
            "status":           "pending",
            "claim_message_id": claim_msg_id,
        }
        save_submissions(submissions)


# ════════════════════════════════════════════════════════════════
#  TASK MANAGEMENT
# ════════════════════════════════════════════════════════════════

class TaskCreateModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📋 Create New Order")
        self.add_item(discord.ui.InputText(label="Order Name", placeholder="e.g. Collect Wood", min_length=1, max_length=100, style=discord.InputTextStyle.short))
        self.add_item(discord.ui.InputText(label="Points per Completion (integer)", placeholder="e.g. 10", min_length=1, max_length=6, style=discord.InputTextStyle.short))
        self.add_item(discord.ui.InputText(label="Max Completions per Member (0 = unlimited)", placeholder="e.g. 5   |   0 for unlimited", min_length=1, max_length=4, style=discord.InputTextStyle.short))

    async def callback(self, interaction: discord.Interaction):
        task_name  = self.children[0].value.strip()
        points_raw = self.children[1].value.strip()
        max_raw    = self.children[2].value.strip()
        errors = []
        try:
            points = int(points_raw)
            if points <= 0: errors.append("Points must be a **positive integer**.")
        except ValueError:
            points = None
            errors.append("Points is not a valid integer.")
        try:
            max_completions = int(max_raw)
            if max_completions < 0: errors.append("Max completions cannot be negative.")
        except ValueError:
            max_completions = None
            errors.append("Max completions is not a valid integer.")
        if errors:
            await interaction.response.send_message("❌ **Error:**\n" + "\n".join(f"• {e}" for e in errors), ephemeral=True)
            await send_control_message(interaction.channel)
            return
        tasks    = load_tasks()
        task_key = task_name.lower().replace(" ", "_")
        if task_key in tasks:
            await interaction.response.send_message(f"⚠️ An order named **{task_name}** already exists.", ephemeral=True)
            await send_control_message(interaction.channel)
            return
        tasks[task_key] = {"name": task_name, "points": points, "max_completions": max_completions}
        save_tasks(tasks)
        max_display = "Unlimited" if max_completions == 0 else str(max_completions)
        embed = discord.Embed(title="✅ Order Created", color=discord.Color.green())
        embed.add_field(name="📌 Order",                value=task_name,   inline=False)
        embed.add_field(name="⭐ Points per Completion", value=str(points), inline=True)
        embed.add_field(name="🔄 Max Completions",       value=max_display, inline=True)
        embed.set_footer(text=f"Created by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
        await send_control_message(interaction.channel)
        await update_open_tasks_channel(interaction.guild)


class TaskDeleteButton(discord.ui.Button):
    def __init__(self, task_key: str, task_name: str, row: int):
        super().__init__(label="Delete", style=discord.ButtonStyle.red, emoji="🗑️", custom_id=f"del_{task_key}", row=row)
        self.task_key  = task_key
        self.task_name = task_name

    async def callback(self, interaction: discord.Interaction):
        if not has_admin_role(interaction):
            await interaction.response.send_message(f"🚫 You need the **{ADMIN_ROLE_NAME}** role.", ephemeral=True)
            return
        tasks = load_tasks()
        if self.task_key not in tasks:
            await interaction.response.send_message(f"⚠️ **{self.task_name}** has already been deleted.", ephemeral=True)
        else:
            del tasks[self.task_key]
            save_tasks(tasks)
            embed = discord.Embed(title="🗑️ Order Deleted", color=discord.Color.red())
            embed.add_field(name="Order", value=self.task_name, inline=False)
            embed.set_footer(text=f"Deleted by {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        task_channel = discord.utils.get(interaction.guild.text_channels, name=TASK_CHANNEL_NAME)
        if task_channel:
            await send_control_message(task_channel)
        await update_open_tasks_channel(interaction.guild)


class NavButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, target_page: int, row: int):
        super().__init__(label=label, style=discord.ButtonStyle.grey, custom_id=custom_id, row=row)
        self.target_page = target_page

    async def callback(self, interaction: discord.Interaction):
        tasks    = load_tasks()
        new_view = DeleteTaskView(tasks, page=self.target_page)
        await interaction.response.edit_message(embed=new_view.build_embed(), view=new_view)


class DeleteTaskView(discord.ui.View):
    TASKS_PER_PAGE = 5

    def __init__(self, tasks: dict, page: int = 0):
        super().__init__(timeout=120)
        self.all_tasks   = list(tasks.items())
        self.page        = page
        self.total_pages = max(1, -(-len(self.all_tasks) // self.TASKS_PER_PAGE))
        start            = page * self.TASKS_PER_PAGE
        self.page_tasks  = self.all_tasks[start : start + self.TASKS_PER_PAGE]
        for row_idx, (task_key, task) in enumerate(self.page_tasks):
            self.add_item(TaskDeleteButton(task_key, task["name"], row=row_idx))
        if self.total_pages > 1:
            if page > 0:
                self.add_item(NavButton("◀ Previous", "nav_prev", page - 1, row=4))
            if page < self.total_pages - 1:
                self.add_item(NavButton("Next ▶", "nav_next", page + 1, row=4))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🗑️ Delete Order", description="Press **Delete** next to the order you want to remove:", color=discord.Color.red())
        for task_key, task in self.page_tasks:
            max_display = "Unlimited" if task["max_completions"] == 0 else f"{task['max_completions']}x"
            embed.add_field(name=f"📌 {task['name']}", value=f"⭐ **{task['points']} Points** | 🔄 Max. **{max_display}**", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
        if self.total_pages > 1:
            embed.set_footer(text=f"Page {self.page + 1} / {self.total_pages}")
        return embed


class TaskControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Order", style=discord.ButtonStyle.green, emoji="➕", custom_id="btn_create_order")
    async def create_order(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not has_admin_role(interaction):
            await interaction.response.send_message(f"🚫 You need the **{ADMIN_ROLE_NAME}** role.", ephemeral=True)
            return
        await interaction.response.send_modal(TaskCreateModal())

    @discord.ui.button(label="Delete Order", style=discord.ButtonStyle.red, emoji="🗑️", custom_id="btn_delete_order")
    async def delete_order(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not has_admin_role(interaction):
            await interaction.response.send_message(f"🚫 You need the **{ADMIN_ROLE_NAME}** role.", ephemeral=True)
            return
        tasks = load_tasks()
        if not tasks:
            await interaction.response.send_message("📭 No orders available to delete.", ephemeral=True)
            return
        view = DeleteTaskView(tasks, page=0)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


# ── Bot Events ────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot online: {bot.user}")
    
    # Register persistent views
    bot.add_view(TaskControlView())
    bot.add_view(ClaimControlView())
    submissions = load_submissions()
    for sub_id, sub in submissions.items():
        if sub.get("status") == "pending":
            bot.add_view(ApprovalView(sub_id))
    
    # Start scheduled tasks (only once)
    if not check_resets.is_running():
        check_resets.start()
    
    # Initialize channels
    for guild in bot.guilds:
        try:
            task_channel = discord.utils.get(guild.text_channels, name=TASK_CHANNEL_NAME)
            if task_channel:
                await send_control_message(task_channel)
            await update_open_tasks_channel(guild)
            claim_channel = discord.utils.get(guild.text_channels, name=CLAIM_CHANNEL_NAME)
            if claim_channel:
                await send_claim_message(claim_channel)
            await update_leaderboard_channel(guild, "weekly")
            await update_leaderboard_channel(guild, "monthly")
        except Exception as e:
            print(f"⚠️ Error initializing {guild.name}: {e}")


if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        print("🛑 Bot stopped")
    except Exception as e:
        print(f"❌ Bot error: {e}")
