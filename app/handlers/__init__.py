from dataclasses import dataclass

from .filters import filter_for_command
from .handlers import start, create_order, calendar, share_event, invite_user, create_event, handle_invite_response
from telegram.ext import CommandHandler, CallbackQueryHandler, BaseHandler
from app.handlers.waiter_commands import waiter_start, waiter_finish_order
from app.core.users.constants import RolesEnum


@dataclass
class Handler:
    handler: BaseHandler
    role: RolesEnum | None = None


HANDLERS = [
    Handler(handler=CommandHandler("start", waiter_start), role=RolesEnum.waiter),
    Handler(handler=CommandHandler("start", start)),
    Handler(handler=CallbackQueryHandler(create_order, pattern=filter_for_command("order_create"))),
    Handler(handler=CommandHandler("calendar", calendar)),
    Handler(handler=CommandHandler("share", share_event)),
    Handler(handler=CommandHandler("invite", invite_user)),
    Handler(handler=CommandHandler("create", create_event)),
    Handler(handler=CallbackQueryHandler(waiter_finish_order, pattern=filter_for_command("waiter_finish_order")), role=RolesEnum.waiter),
    Handler(handler=CallbackQueryHandler(handle_invite_response, pattern="^invite_")),
]