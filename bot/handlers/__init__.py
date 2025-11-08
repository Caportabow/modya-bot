from .core import callback, chat_member, groups, help
from .functionalities import awards, call, cleaning
from .functionalities import leaderboard, nicknames, quotes
from .functionalities import user_info, warnings, rests

routers = [callback.router, chat_member.router, help.router, leaderboard.router,
           awards.router, call.router, cleaning.router,
           nicknames.router, quotes.router, user_info.router,
           warnings.router, rests.router, groups.router,
]