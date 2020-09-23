from __future__ import unicode_literals
from telegram.ext import (Updater, CommandHandler, MessageHandler, ConversationHandler, Filters, CallbackQueryHandler)
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)
from telegram import (ParseMode, InlineKeyboardButton, InlineKeyboardMarkup)
import requests
from bs4 import BeautifulSoup

ERROR_CODE, ACTIONS = range(2)

def html_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

def keyboard_gen(actions):
    if len(actions) != 0:
        keyboard = []
        for item in actions:
            print(item["value"])
            print(item["next_step_id"])
            keyboard.append([InlineKeyboardButton("🔸 " + item["value"], callback_data = item["next_step_id"])])
        return keyboard




def start(update, context):
    reply_keyboard = [[InlineKeyboardButton("🔓 Codice errore", callback_data = "error_code")], 
                        [InlineKeyboardButton("📝 Descrizione", callback_data = "description")]]
    msg = update.message.bot.send_message(chat_id = update.message.chat_id, 
                                    text = "Benvenuto. Puoi cercare per codice errore o descrizione", 
                                    reply_markup = InlineKeyboardMarkup(reply_keyboard))
    context.user_data["msg"] = msg.message_id
    

def search(update, context):
    if update.callback_query:
        if update.callback_query.data == "description":
            update.callback_query.message.bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = context.user_data["msg"], text = "⚠️ Funzione al momento non disponibile")
            return ConversationHandler.END
        elif update.callback_query.data == "error_code":
            update.callback_query.message.bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = context.user_data["msg"], text = "📭 Mandami il codice errore")
            return ERROR_CODE
        else:
            ConversationHandler.END


def error_code(update, context):
    error_code = update.message.text
    lookup = requests.get("http://demo.knowai.it:10000/core/lookup/code/{}".format(error_code)).json()
    print(lookup)
    print(lookup["status"])
    if lookup["status"] == "success":
        tree_id = lookup["tree_id"]
        context.user_data["tree_id"] = tree_id
        root = requests.get("http://demo.knowai.it:10000/core/visit/root?tree_id={}".format(tree_id)).json()
        print(root)
        if root["status"] == "success":
            root = root["root"]
            actions = requests.get("http://demo.knowai.it:10000/core/visit/step?tree_id={}&step_id={}".format(tree_id,root)).json()
            print(actions)
            if len(actions["actions"]) != 0:
                keyboard = keyboard_gen(actions["actions"]) #funzione che mi genera la tastiera di telegram
                print(keyboard)
                msg = update.message.reply_text("➡️ {}".format(html_content(actions["value"])), reply_markup = InlineKeyboardMarkup(keyboard))
                context.user_data["msg"] = msg.message_id
                return ACTIONS
            else:
                update.message.text("✅ albero finito")
                return ConversationHandler.END

        else:
            update.message.reply_text("❌ ERROR: tree id not found")
            update.message.reply_text("🔁 Prova con un altro codice errore")
            return ERROR_CODE


    else:
        update.message.reply_text("❌ ERROR: error code not found")
        update.message.reply_text("🔁 Prova con un altro codice errore")
        return ERROR_CODE

def step_id(update, context):
    if update.callback_query:
        step_id = update.callback_query.data
        tree_id = context.user_data["tree_id"]
        actions = requests.get("http://demo.knowai.it:10000/core/visit/step?tree_id={}&step_id={}".format(tree_id,step_id)).json()
        if len(actions["actions"]) != 0:
            keyboard = keyboard_gen(actions["actions"]) #funzione che mi genera la tastiera di telegram
            update.callback_query.message.bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = context.user_data["msg"], 
                                                text = "➡️ {}".format(html_content(actions["value"])), reply_markup = InlineKeyboardMarkup(keyboard))
            return ACTIONS
        else:
            update.callback_query.message.bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = context.user_data["msg"], 
                                                text = "➡️ {}".format(html_content(actions["value"])))
            #update.callback_query.message.reply_text("✅ albero finito")
            return ConversationHandler.END

    
def cancel(update, context):
    update.message.reply_text("Process ended")
    return ConversationHandler.END
    




def main():
    updater = Updater(token = "1059982021:AAE80kWJhDj5oBBbOc0nMhoIyRcLdeeLwzk", use_context=True, request_kwargs={'read_timeout': 6, 'connect_timeout': 7})
    
    conv_handler = ConversationHandler(
        entry_points = [CallbackQueryHandler(search)],
        states = {
            ERROR_CODE: [MessageHandler(Filters.text, error_code, pass_user_data = True)],
            ACTIONS: [CallbackQueryHandler(step_id, pass_user_data = True)]
        },

        fallbacks = [CommandHandler("cancel", cancel)]
    )

    dp = updater.dispatcher  
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv_handler)
    updater.start_polling(clean = True)
    updater.idle()




if __name__ == '__main__':
    main()
