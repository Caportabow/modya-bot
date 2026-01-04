from .system import help, chat_members, chat_callbacks, chat_events
from .moderation import call, chat_settings, cleaning, warnings, rests
from .social import awards, game_commands, leaderboard, marriages, nicknames, personal_rp_commands, quotes, user_info

routers = [
    # social
    awards.router,
    game_commands.router,
    leaderboard.router,
    marriages.router,
    nicknames.router,
    personal_rp_commands.router,
    quotes.router,
    user_info.router,

    # moderation
    call.router,
    chat_settings.router,
    cleaning.router,
    warnings.router,
    rests.router,

    # system
    help.router,
    chat_members.router,
    chat_callbacks.router,
    chat_events.router,
]