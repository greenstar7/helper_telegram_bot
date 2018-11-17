import logging
from datetime import datetime
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

TOKEN_FILENAME = '../TOKEN.txt'
EVENT_NAME, EVENT_DATE, EVENT_LOC, EVENT_MSG = range(4)

def read_token(filename):
    with open(filename,'r') as file:
        token = file.readline().strip()
        return token

def event(bot, update):
    update.message.reply_text('Ok.Let\'s create new event!\n'
                              'Send /cancel to cancel the command.\n'
                              'Enter the name of the event you want me to write down:')
    return EVENT_NAME

def event_name(bot, update):
    user = update.message.from_user
    logger.info(f'{user.first_name}\'s event name: {update.message.text}')
    update.message.reply_text('Ok. Now, please, enter the date and time of the {update.message.text}\n'
                              'Please, enter it in the "YYYY-MM-DD HH:MI:SS" format!')
    return EVENT_DATE


def event_date(bot, update):
    user = update.message.from_user
    logger.info(f'{user.first_name}\'s event date: {update.message.text}')
    update.message.reply_text('Done! Now send me the location of the event or /skip:\n')
    return EVENT_LOC


def skip_event_loc(bot, update):
    user = update.message.from_user
    logger.info(f'{user.first_name} did not send a location of the event.')
    update.message.reply_text('Ok! Now send me the message you want me to send '
                              'to you as a reminder for the event or /skip:\n')
    return EVENT_MSG


def event_loc(bot, update):
    user = update.message.from_user
    logger.info(f'{user.first_name}\'s location of the event: {update.message.text}')
    update.message.reply_text('Ok! I\'ve writen down location of the event!\n'
                              'Now send me the message you want me to send you'
                              'as a reminder for the event or /skip:\n')
    return EVENT_MSG

def skip_event_msg(bot, update):
    user = update.message.from_user
    logger.info(f'{user.first_name} did not send a message for the event.')
    update.message.reply_text('Done! I wrote down all the info about the event!')
    return ConversationHandler.END

def event_msg(bot, update):
    user = update.message.from_user
    logger.info(f'{user.first_name}\'s message for the event:\n {update.message.text}')
    update.message.reply_text('Done! I wrote down all the info about the event!')

    return ConversationHandler.END

def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the new event.", user.first_name)
    update.message.reply_text('Ok, I canceled the new event entry!')
    return ConversationHandler.END

def start(bot, update):
    update.message.reply_text('Hi! I\'m orginizer helper bot!\n'
                              'Write /help to see all available commands.')
    
def help(bot, update):
    update.message.reply_text('Currently you can use only:\n'
                              '/set <seconds> [timer_name] [timer_message] - to set timer.\n'
                              '/new_event <date "YYYY-MM-DD"> <time "HH:MI:SS">'
                              '<event_name> [event_message]- to create an new event')
    
def alarm(bot, job):
    """Send the alarm message."""
    chat_id = job.context[0]
    job_name = job.context[1]
    job_message = job.context[2]
    bot.send_message(chat_id, text=f'{job_name}: {job_message}')

def set_timer(bot, update, args, job_queue, chat_data):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(args[0])
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds> [timer_name] [timer_message]') 
        
    try:
        # args[1] should contain the name of the timer
        timer_name = args[1]
    except IndexError:
        timer_name = 'timer'
        
    if args[2:]:
        timer_message = ' '.join(args[2:])
    else:
        timer_message = 'beep!'
        
    if timer_name in chat_data:
        update.message.reply_text(f'Updating \'{timer_name}\' timer')
        timer = chat_data[timer_name]
        timer.schedule_removal()
        
    timer = job_queue.run_once(alarm, due, context=[chat_id, timer_name, timer_message])
    chat_data[timer_name] = timer
    update.message.reply_text(f'Timer \'{timer_name}\' successfully set!')
    
        
def new_event(bot, update, args, job_queue, chat_data):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        date = args[0]
        time = args[1]
        event_date = datetime.strptime(' '.join((date, time)), '%Y-%m-%d %H:%M:%S')
        if event_date < datetime.now():
            update.message.reply_text('Sorry we can not go back to future!')
            return
        event_name = args[2]
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /new_event <date "YYYY-MM-DD">'
                                  '<time "HH:MI:SS"> <event_name> [event_message]')
    if args[3:]:
        event_message = ' '.join(args[3:])
        
    if event_name in chat_data:
        update.message.reply_text(f'Updating \'{event_name}\' event')
        event = chat_data[event_name]
        event.schedule_removal()
        
    event = job_queue.run_once(alarm, when=event_date, context=[chat_id, event_name, event_message])
    chat_data[event_name] = event
    update.message.reply_text(f'Event {event_name} successfully set!')

def unset(bot, update, args, chat_data):
    """Remove the job if the user changed their mind."""
    try:
        job_name = ' '.join(args[0:])
    except IndexError:
        job_name = 'timer'
        
    if job_name not in chat_data:
        update.message.reply_text(f'You have no active {job_name}.')
        return
    
    job = chat_data[job_name]
    job.schedule_removal()
    del chat_data[job]

    update.message.reply_text(f'{job_name} successfully unset!')


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def main():
    updater = Updater(read_token(TOKEN_FILENAME))
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler("set", set_timer,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    
    dispatcher.add_handler(CommandHandler("new_event", new_event,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    
    dispatcher.add_handler(CommandHandler("unset", unset,
                                          pass_args=True,
                                          pass_chat_data=True))

    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('event', event)],

        states={
            EVENT_NAME: [MessageHandler(Filters.text, event_name)],
            EVENT_DATE: [MessageHandler(Filters.text, event_date)],
            EVENT_LOC: [MessageHandler(Filters.text, event_loc),
                        CommandHandler('skip', skip_event_loc)],
            EVENT_MSG: [MessageHandler(Filters.text, event_msg),
                        CommandHandler('skip', skip_event_msg)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)
    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__=='__main__':
    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    logger = logging.getLogger(__name__)
    main()
