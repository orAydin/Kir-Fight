from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services import UserService, ChallengeService, QuestService
from config import config
import logging

logger = logging.getLogger(__name__)

class CommandHandlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        group_id = str(update.effective_chat.id)
        username = update.effective_user.username or update.effective_user.first_name
        
        # Create default quests for new groups
        QuestService.create_default_quests(group_id)
        
        welcome_text = (
            "🎉 به مسابقه کیر کلفتا خوش اومدی!\n\n"
            "🎯 دستورات موجود:\n"
            "/grow - روزانه کیرت رو بزرگ کن\n"
            "/leaderboard - جدول امتیازات\n"
            "/challenge - چالش کن\n"
            "/quests - ماموریت‌ها\n"
            "/stats - آمار شخصی\n"
            "/help - راهنما"
        )
        
        await update.message.reply_text(welcome_text)
    
    @staticmethod
    async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 راهنمای کامل:\n\n"
            "🌱 /grow - هر روز یکبار استفاده کن تا کیرت بزرگ شه\n"
            "🏆 /leaderboard - ببین تو جدول چندمی\n"
            "⚔️ /challenge [مقدار] - با ریپلای کردن کسی رو چالش کن\n"
            "📜 /quests - ماموریت‌هات رو ببین\n"
            "📊 /stats - آمار کاملت رو ببین\n"
            "🔊 /echo - متن ریپلای شده رو تکرار کن\n\n"
            "💡 نکته: برای چالش، مقدار رو هم بنویس مثل:\n"
            "/challenge 10"
        )
        await update.message.reply_text(help_text)
    
    @staticmethod
    async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.reply_to_message:
            replied_text = update.message.reply_to_message.text
            await update.message.reply_text(f"🔊 پیام تکرار شده: {replied_text}")
        else:
            await update.message.reply_text("⚠️ برای تکرار پیام، ابتدا به پیامی ریپلای کن")
    
    @staticmethod
    async def grow(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        group_id = str(update.effective_chat.id)
        username = update.effective_user.username or update.effective_user.first_name
        
        try:
            success, message, growth, new_length = UserService.grow_user(user_id, group_id, username)
            await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error in grow command: {e}")
            await update.message.reply_text("⚠️ خطا در انجام عملیات")
    
    @staticmethod
    async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
        group_id = str(update.effective_chat.id)
        
        try:
            top_users = UserService.get_leaderboard(group_id)
            
            if not top_users:
                await update.message.reply_text("📋 هنوز کسی در مسابقه شرکت نکرده!")
                return
            
            leaderboard_text = "🏆 جدول کیرکلفتا 🏆\n\n"
            medals = ["🥇", "🥈", "🥉"]
            
            for i, user in enumerate(top_users, 1):
                medal = medals[i-1] if i <= 3 else f"{i}."
                win_rate = f" (W: {user.win_rate:.1f}%)" if user.total_challenges > 0 else ""
                leaderboard_text += f"{medal} {user.username}: {user.length} cm{win_rate}\n"
            
            await update.message.reply_text(leaderboard_text)
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await update.message.reply_text("⚠️ خطا در دریافت جدول امتیازات")
    
    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        group_id = str(update.effective_chat.id)
        
        try:
            user = UserService.get_user_stats(user_id, group_id)
            if not user:
                await update.message.reply_text("⚠️ ابتدا با دستور /grow در مسابقه شرکت کن")
                return
            
            stats_text = (
                f"📊 آمار {user.username}:\n\n"
                f"📏 طول: {user.length} سانتی‌متر\n"
                f"⚔️ کل چالش‌ها: {user.total_challenges}\n"
                f"🏆 برد: {user.challenges_won}\n"
                f"📈 درصد برد: {user.win_rate:.1f}%\n"
                f"📅 آخرین رشد: {user.last_growth or 'هنوز نداشته'}"
            )
            
            await update.message.reply_text(stats_text)
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("⚠️ خطا در دریافت آمار")

class ChallengeHandlers:
    @staticmethod
    async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ برای چالش باید به پیام کسی ریپلای کنی")
            return
        
        try:
            challenge_value = int(context.args[0]) if context.args else 5
            if challenge_value < config.min_challenge_amount or challenge_value > config.max_challenge_amount:
                await update.message.reply_text(
                    f"⚠️ مقدار چالش باید بین {config.min_challenge_amount} تا {config.max_challenge_amount} سانتی‌متر باشه"
                )
                return
        except (ValueError, IndexError):
            challenge_value = 5
        
        challenger_id = str(update.effective_user.id)
        challenger_name = update.effective_user.username or update.effective_user.first_name
        opponent_id = str(update.message.reply_to_message.from_user.id)
        opponent_name = update.message.reply_to_message.from_user.username or update.message.reply_to_message.from_user.first_name
        group_id = str(update.effective_chat.id)
        
        try:
            can_challenge, message = ChallengeService.can_challenge(
                challenger_id, opponent_id, group_id, challenge_value
            )
            
            if not can_challenge:
                await update.message.reply_text(message)
                return
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ قبول", callback_data=f"accept_{challenger_id}_{challenge_value}_{group_id}_{opponent_id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"decline_{challenger_id}_{group_id}_{opponent_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚔️ {opponent_name}, {challenger_name} بهت چالش داده!\n"
                f"💰 مقدار: {challenge_value} سانتی‌متر\n"
                f"🎯 آماده‌ای؟",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in challenge command: {e}")
            await update.message.reply_text("⚠️ خطا در ایجاد چالش")
    
    @staticmethod
    async def handle_challenge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data_parts = query.data.split('_')
        action = data_parts[0]
        challenger_id = data_parts[1]
        
        if action == "accept":
            challenge_value = int(data_parts[2])
            callback_group_id = data_parts[3]
            opponent_id_expected = data_parts[4]
        else:
            callback_group_id = data_parts[2]
            opponent_id_expected = data_parts[3]
        
        opponent_id_actual = str(query.from_user.id)
        current_group_id = str(query.message.chat.id)
        
        # Validation
        if callback_group_id != current_group_id:
            await query.answer("این چالش برای این گروه نیست!", show_alert=True)
            return
        
        if opponent_id_actual != opponent_id_expected:
            await query.answer("فقط کسی که بهش چالش دادی می‌تونه جواب بده!", show_alert=True)
            return
        
        if action == "decline":
            await query.edit_message_text("❌ چالش رد شد!")
            return
        
        try:
            winner_id, loser_id, winner_new_length, loser_new_length = ChallengeService.execute_challenge(
                challenger_id, opponent_id_actual, current_group_id, challenge_value
            )
            
            # Get usernames for display
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id, username FROM users WHERE (user_id = ? OR user_id = ?) AND group_id = ?",
                    (winner_id, loser_id, current_group_id)
                )
                users = {row['user_id']: row['username'] for row in cursor.fetchall()}
            
            winner_name = users[winner_id]
            loser_name = users[loser_id]
            
            await query.edit_message_text(
                f"🎉 نتیجه چالش:\n\n"
                f"🏆 برنده: {winner_name}\n"
                f"📏 طول جدید: {winner_new_length} cm (+{challenge_value})\n\n"
                f"😔 بازنده: {loser_name}\n"
                f"📏 طول جدید: {loser_new_length} cm (-{challenge_value})"
            )
        except Exception as e:
            logger.error(f"Error in challenge execution: {e}")
            await query.answer("⚠️ خطا در انجام چالش", show_alert=True)

class QuestHandlers:
    @staticmethod
    async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        group_id = str(update.effective_chat.id)
        
        try:
            active_quests = QuestService.get_active_quests(group_id)
            if not active_quests:
                await update.message.reply_text("📜 در حال حاضر هیچ ماموریتی موجود نیست!")
                return
            
            user_progress = QuestService.get_user_quest_progress(user_id, group_id)
            
            message = "📜 ماموریت‌های فعال:\n\n"
            for quest in active_quests:
                progress = user_progress.get(quest.quest_id)
                if progress and progress.completed:
                    status = "✅ تکمیل شده"
                elif progress:
                    percentage = min(100, (progress.progress / quest.target_value) * 100)
                    status = f"⏳ {progress.progress}/{quest.target_value} ({percentage:.1f}%)"
                else:
                    status = f"⏳ 0/{quest.target_value} (0%)"
                
                message += (
                    f"🎯 {quest.title}\n"
                    f"📝 {quest.description}\n"
                    f"💰 جایزه: {quest.reward} سانتی‌متر\n"
                    f"📊 پیشرفت: {status}\n\n"
                )
            
            await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error in quests command: {e}")
            await update.message.reply_text("⚠️ خطا در دریافت ماموریت‌ها")
