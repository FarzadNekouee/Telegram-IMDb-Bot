from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, InlineQueryHandler, MessageHandler, Filters
import requests

# Telegram Bot API key
API_KEY = "your_telegram_bot_api_key"  

# IMDb API key   
IMDB_API_KEY = "your_imdb_api_key"

# Store users' watchlists as a dictionary
user_watchlists = {}

# Welcome message when the bot starts
def start(update: Update, context):
    message = "👋 Welcome to the IMDb Movie Bot!\n\n📽️ You can access the bot tools through the Menu."
    update.message.reply_text(message)

# Restart message when the user sends /restart command
def restart(update: Update, context):
    message = "🔄 To restart the bot, please close and reopen the chat with the bot, or send the /start command again."
    update.message.reply_text(message)

# Display available tools when the user sends /tools command
def tools(update: Update, context):
    message = "🔎 Choose a tool:"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎬 Search Movie", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("📋 View Watchlist", callback_data="view_watchlist")],
        ]
    )
    update.message.reply_text(message, reply_markup=keyboard)  # Send the message with the inline keyboard

# Handle callback queries (button clicks)
def handle_callback_query(update: Update, context):
    query = update.callback_query
    data = query.data
    
    # Handle "view_watchlist" button click
    if data == "view_watchlist":
        user_id = query.from_user.id

        if user_id not in user_watchlists or not user_watchlists[user_id]:
            query.message.reply_text("🚫 Your watchlist is empty.")
        else:
            keyboard = [
                [
                    InlineKeyboardButton(f"{i+1}. {title}", callback_data=f"movie_in_watchlist:{movie_id}:{title}"),
                    InlineKeyboardButton("🗑️", callback_data=f"delete_from_watchlist:{movie_id}")
                ]
                for i, (movie_id, title) in enumerate(user_watchlists[user_id].items())
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text("👁️ Your watchlist:", reply_markup=reply_markup)
    
    # Handle "delete_from_watchlist" button click
    elif data.startswith("delete_from_watchlist:"):
        _, movie_id = data.split(":", 1)
        user_id = query.from_user.id

        if user_id in user_watchlists and movie_id in user_watchlists[user_id]:
            del user_watchlists[user_id][movie_id]
            query.answer("✅ Movie removed from your watchlist!")
            # Call view_watchlist again to display the updated watchlist
            query.data = "view_watchlist"
            handle_callback_query(update, context)
        else:
            query.answer("ℹ️ Movie not found in your watchlist.")
            
    # Handle "movie_in_watchlist" button click
    elif data.startswith("movie_in_watchlist:"):
        _, movie_id, title = data.split(":", 2)
        query.answer(f"ℹ️ {title} is in your watchlist!")
    
    # Handle "add_to_watchlist" button click
    elif data.startswith("add_to_watchlist:"):
        _, movie_id, movie_title = data.split(":", 2)
        user_id = query.from_user.id

        if user_id not in user_watchlists:
            user_watchlists[user_id] = {}

        if movie_id not in user_watchlists[user_id]:
            user_watchlists[user_id][movie_id] = movie_title
            query.answer("✅ Movie added to your watchlist!")
        else:
            query.answer("ℹ️ Movie is already in your watchlist.")
    
    # Handle "view_images" button click
    elif data.startswith("view_images:"):
        _, movie_id, movie_title = data.split(":", 2)
        
        images_url = f"https://imdb-api.com/en/API/Images/{IMDB_API_KEY}/{movie_id}"
        images_response = requests.get(images_url).json()
        image_items = images_response.get("items")[:10]

        if image_items:
            media_group = [InputMediaPhoto(media=item["image"]) for item in image_items]
            query.bot.send_media_group(chat_id=query.message.chat_id, media=media_group)
        else:
            query.answer("🚫 Sorry, no images are available for this movie.")

        # Fetch the trailer_link
        trailer_url = f"https://imdb-api.com/en/API/Trailer/{IMDB_API_KEY}/{movie_id}"
        trailer_response = requests.get(trailer_url).json()
        trailer_link = trailer_response.get("link")

        keyboard = [
            [
                InlineKeyboardButton("🎞️ Watch Trailer", url=trailer_link) if trailer_link else InlineKeyboardButton("🎞️ Trailer not available", callback_data="trailer_not_available"),
            ],
            [
                InlineKeyboardButton("➕ Add to Watchlist", callback_data=f"add_to_watchlist:{movie_id}:{movie_title}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(f"🎬 *{movie_title}* Movie Images", reply_markup=reply_markup, parse_mode='Markdown')

# Handle inline search for movies
def inline_search_movies(update: Update, context):
    query = update.inline_query.query
    url = f"https://imdb-api.com/en/API/SearchMovie/{IMDB_API_KEY}/{query}"
    response = requests.get(url).json()

    results = []
    
    # Create search results
    for movie in response["results"]:
        results.append(
            InlineQueryResultArticle(
                id=movie["id"],
                title=movie["title"],
                description=movie["description"],
                thumb_url=movie["image"],
                input_message_content=InputTextMessageContent(movie["id"]),
            )
        )

    update.inline_query.answer(results)

# Display movie details when a movie ID is sent as a message
def display_movie_details(update: Update, context):
    movie_id = update.message.text
    message_id = update.message.message_id
    chat_id = update.message.chat_id
    
    # Fetch movie details
    url = f"https://imdb-api.com/en/API/Title/{IMDB_API_KEY}/{movie_id}/"
    response = requests.get(url).json()
    
    # Prepare and send movie details message
    rating_votes = int(response['imDbRatingVotes'])
    rating_votes_in_millions = rating_votes / 1_000_000
    formatted_rating_votes = f"{rating_votes_in_millions:.1f}M"
    details = (
        f"🎬 *Title:* {response['fullTitle']}\n\n"
        f"⭐ *Rating:* {response['imDbRating']} ({formatted_rating_votes} votes)\n"
        f"📅 *Release Date:* {response['releaseDate']}\n"
        f"🌐 *Languages:* {response['languages']}\n"
        f"🌍 *Countries:* {response['countries']}\n\n"
        f"⌛ *Duration:* {response['runtimeStr']}\n"
        f"🎭 *Genres:* {response['genres']}\n\n"
        f"🌟 *Stars:* {response['stars']}\n"
        f"🎥 *Directors:* {response['directors']}\n"
        f"✍ *Writers:* {response['writers']}\n"
        f"🏆 *Awards:* {response['awards']}\n\n"
        f"📖 *Story Line:*\n {response['plot']}\n"
    )

    trailer_url = f"https://imdb-api.com/en/API/Trailer/{IMDB_API_KEY}/{movie_id}"
    trailer_response = requests.get(trailer_url).json()
    trailer_link = trailer_response.get("link")

    short_title = response['fullTitle'][:30] + '...' if len(response['fullTitle']) > 30 else response['fullTitle']

    keyboard = [
        [
            InlineKeyboardButton("📸 View Images", callback_data=f"view_images:{movie_id}:{short_title}"),
            InlineKeyboardButton("🎞️ Watch Trailer", url=trailer_link) if trailer_link else InlineKeyboardButton("🎞️ Trailer not available", callback_data="trailer_not_available"),
        ],
        [
            InlineKeyboardButton("➕ Add to Watchlist", callback_data=f"add_to_watchlist:{movie_id}:{short_title}"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_photo(photo=response["image"], caption=details, reply_markup=reply_markup, parse_mode="Markdown")
    
    # Delete the message containing the movie ID
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)

# Main function to set up handlers and start the bot
def main():
    updater = Updater(API_KEY)
    dispatcher = updater.dispatcher
    
    # Add command handlers for /start, /tools, and /restart
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("tools", tools))
    dispatcher.add_handler(CommandHandler("restart", restart))
    
    # Add callback query handler for handling button clicks
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add inline query handler for searching movies
    dispatcher.add_handler(InlineQueryHandler(inline_search_movies))
    
    # Add message handler for displaying movie details
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, display_movie_details))
    
    # Start the bot
    updater.start_polling()
    updater.idle()

# Run the main function when the script is executed
if __name__ == "__main__":
    main()