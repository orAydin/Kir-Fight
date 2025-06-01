import logging
import threading
import os
from flask import Flask
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import config
from database import db_manager
from handlers import CommandHandlers, ChallengeHandlers, QuestHandlers

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.log_level),
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask app for health check
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Bot is running successfully!"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "dick_competition_bot"}

def run_flask():
    """Run Flask server in a separate thread"""
    app.run(host='0.0.0.0', port=config.port, debug=False)

async def error_handler(update, context):
    """Handle bot errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    logger.info("🚀 Starting Dick Competition Bot...")
    
    try:
        # Initialize database
        db_manager.migrate_database()
        db_manager.initialize_database()
        logger.info("✅ Database initialized successfully")
        
        # Start Flask server
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info(f"✅ Flask server started on port {config.port}")
        
        # Build application
        application = Application.builder().token(config.token).build()
        
        # Register command handlers
        application.add_handler(CommandHandler("start", CommandHandlers.start))
        application.add_handler(CommandHandler("help", CommandHandlers.help))
        application.add_handler(CommandHandler("echo", CommandHandlers.echo))
        application.add_handler(CommandHandler("grow", CommandHandlers.grow))
        application.add_handler(CommandHandler("leaderboard", CommandHandlers.leaderboard))
        application.add_handler(CommandHandler("stats", CommandHandlers.stats))
        application.add_handler(CommandHandler("challenge", ChallengeHandlers.challenge))
        application.add_handler(CommandHandler("quests", QuestHandlers.quests))
        
        # Register callback handlers
        application.add_handler(CallbackQueryHandler(
            ChallengeHandlers.handle_challenge_callback, 
            pattern="^(accept|decline)_"
        ))
        
        # Register error handler
        application.add_error_handler(error_handler)
        
        logger.info("✅ All handlers registered successfully")
        
        # Start polling
        logger.info("🔄 Starting bot polling...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise

if __name__ == '__main__':
    main()
