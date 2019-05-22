# SCP-079-USER - Invite and help other bots
# Copyright (C) 2019 SCP-079 <https://scp-079.org>
#
# This file is part of SCP-079-USER.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from time import sleep
from typing import List, Optional, Union

from pyrogram import Chat, Client, Message
from pyrogram.errors import FloodWait

from .. import glovar
from .etc import code, general_link, format_data, thread, user_mention
from .file import crypt_file
from .telegram import get_group_info, send_document, send_message

# Enable logging
logger = logging.getLogger(__name__)


def declare_message(client: Client, gid: int, mid: int) -> bool:
    # Declare a message
    try:
        glovar.declared_message_ids[gid].add(mid)
        share_data(
            client=client,
            receivers=glovar.receivers_declare,
            action="update",
            action_type="declare",
            data={
                "group_id": gid,
                "message_id": mid
            }
        )
        return True
    except Exception as e:
        logger.warning(f"Declare message error: {e}", exc_info=True)

    return False


def exchange_to_hide(client: Client) -> bool:
    # Let other bots exchange data in the hide channel instead
    try:
        glovar.should_hide = True
        text = format_data(
            sender="EMERGENCY",
            receivers=["EMERGENCY"],
            action="backup",
            action_type="hide",
            data=True
        )
        thread(send_message, (client, glovar.hide_channel_id, text))
        return True
    except Exception as e:
        logger.warning(f"Exchange to hide error: {e}", exc_info=True)

    return False


def forward_evidence(client: Client, message: Message, level: str, rule: str) -> Optional[Union[bool, int]]:
    # Forward the message to the logging channel as evidence
    result = None
    try:
        if not message or not message.from_user:
            return result

        uid = message.from_user.id
        flood_wait = True
        while flood_wait:
            flood_wait = False
            try:
                result = message.forward(glovar.logging_channel_id)
            except FloodWait as e:
                flood_wait = True
                sleep(e.x + 1)
            except Exception as e:
                logger.info(f"Forward evidence message error: {e}", exc_info=True)
                return False

        result = result.message_id
        text = (f"项目编号：{code(glovar.sender)}\n"
                f"用户 ID：{code(uid)}\n"
                f"操作等级：{code(level)}\n"
                f"规则：{code(rule)}\n")
        thread(send_message, (client, glovar.logging_channel_id, text, result))
    except Exception as e:
        logger.warning(f"Forward evidence error: {e}", exc_info=True)

    return result


def get_debug_text(client: Client, context: Union[int, Chat]) -> str:
    # Get a debug message text prefix, accept int or Chat
    if isinstance(context, int):
        info_para = context
        id_para = context
    else:
        info_para = context
        id_para = context.id

    group_name, group_link = get_group_info(client, info_para)
    text = (f"项目编号：{general_link(glovar.project_name, glovar.project_link)}\n"
            f"群组名称：{general_link(group_name, group_link)}\n"
            f"群组 ID：{code(id_para)}\n")

    return text


def send_debug(client: Client, chat: Chat, action: str, uid: int, mid: int, eid: int) -> bool:
    # Send the debug message
    text = get_debug_text(client, chat)
    text += (f"用户 ID：{user_mention(uid)}\n"
             f"执行操作：{code(action)}\n"
             f"触发消息：{general_link(mid, f'https://t.me/{glovar.logging_channel_username}/{eid}')}\n")
    thread(send_message, (client, glovar.debug_channel_id, text))

    return False


def share_data(client: Client, receivers: List[str], action: str, action_type: str, data: Union[dict, int, str],
               file: str = None) -> bool:
    # Use this function to share data in the exchange channel
    try:
        if glovar.sender in receivers:
            receivers.remove(glovar.sender)

        if glovar.should_hide:
            channel_id = glovar.hide_channel_id
        else:
            channel_id = glovar.exchange_channel_id

        if file:
            text = format_data(
                sender=glovar.sender,
                receivers=receivers,
                action=action,
                action_type=action_type,
                data=data
            )
            crypt_file("encrypt", f"data/{file}", f"tmp/{file}")
            result = send_document(client, channel_id, f"tmp/{file}", text)
        else:
            text = format_data(
                sender=glovar.sender,
                receivers=receivers,
                action=action,
                action_type=action_type,
                data=data
            )
            result = send_message(client, channel_id, text)

        if result is False:
            exchange_to_hide(client)
            thread(share_data, (client, receivers, action, action_type, data, file))

        return True
    except Exception as e:
        logger.warning(f"Share data error: {e}", exc_info=True)

    return False
