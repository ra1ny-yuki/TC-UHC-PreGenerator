import os
import time
from typing import Optional

from mcdreforged.api.all import *

from tcuhc_pregen.config import config
from tcuhc_pregen.sessions import RunningSession, PreGenerationSession, LoadSlotSession, RemoveSlotSession, \
    AutoRemoveSlotSession
from tcuhc_pregen.storage import storage, SlotInfo
from tcuhc_pregen.utils import global_psi, htr, tr, DEBUG


class SlotNotFound(CommandError):
    def __init__(self, slot_name: Optional[str] = None):
        super(SlotNotFound, self).__init__('', '', '')
        self.slot_name = slot_name


def get_slot(slot_name: str) -> SlotInfo:
    slot_info = storage.get_slots_info(allow_used=True).get(slot_name)
    if slot_info is None:
        raise SlotNotFound(slot_name)
    return slot_info


def confirm_or_abort():
    return tr(
        'msg.confirm_abort',
        RText(f'{config.prefix[0]} confirm', color=RColor.gray).h(tr('hover.to_confirm')).c(RAction.run_command, f'{config.prefix[0]} confirm'),
        RText(f'{config.prefix[0]} abort', color=RColor.gray).h(tr('hover.to_abort')).c(RAction.run_command, f'{config.prefix[0]} abort')
    )


def show_help(src: CommandSource):
    src.reply(tr('help.detailed', prefix=config.prefix[0]).set_translator(htr))


def pre_generate_worlds(src: CommandSource, num: int = config.default_slots, comment: str = ''):
    if not RunningSession.is_avail():
        src.reply(tr('error.not_avail').set_color(RColor.red))
        return
    generated_slot_num = len(storage.get_slots_info(allow_used=True))
    if generated_slot_num + num > config.max_slots:
        src.reply(tr('error.not_enough_slot'))
        return
    RunningSession.running_session = PreGenerationSession(num, comment)
    src.reply(tr('ask.pregen', num) + '\n' + confirm_or_abort())


def load_pre_generated_world(src: CommandSource, slot_name: Optional[str] = None):
    if not RunningSession.is_avail():
        src.reply(tr('error.not_avail').set_color(RColor.red))
        return
    slot_name = tuple(storage.get_slots_info().keys())[0] if slot_name is None else slot_name
    get_slot(slot_name)
    RunningSession.running_session = LoadSlotSession(slot_name)
    src.reply(tr('ask.load', slot_name) + '\n' + confirm_or_abort())


def remove_pre_generated_world(src: CommandSource, slot_name: Optional[str] = None):
    if not RunningSession.is_avail():
        src.reply(tr('error.not_avail').set_color(RColor.red))
        return
    get_slot(slot_name)
    RunningSession.running_session = RemoveSlotSession(slot_name)
    src.reply(tr('ask.remove', slot_name) + '\n' + confirm_or_abort())


def auto_remove_used_world(src: CommandSource):
    if not RunningSession.is_avail():
        src.reply(tr('error.not_avail').set_color(RColor.red))
        return
    RunningSession.running_session = AutoRemoveSlotSession()
    src.reply(tr('ask.auto_remove') + '\n' + confirm_or_abort())


def single_info(dir_name: str, used: bool = False):
    return RTextList(
        RText('[▷] ', color=RColor.green).h(tr('hover.load', dir_name)).c(
            RAction.run_command, f'{config.prefix[0]} load {dir_name}'),
        RText('[×] ', color=RColor.red).h(tr('hover.remove', dir_name)).c(
            RAction.run_command, f'{config.prefix[0]} del {dir_name}'),
        RText(
            dir_name, color=RColor.gray if used else RColor.yellow, styles=RStyle.strikethrough if used else None
        ).h(tr('hover.info', dir_name)).c(
            RAction.run_command, f'{config.prefix[0]} info {dir_name}'
        )
    )


def reload_self(src: CommandSource, throw_session=False):
    if throw_session:
        RunningSession.clear()
    global_psi.reload_plugin(global_psi.get_self_metadata().id)
    src.reply(tr('msg.reloaded'))


def list_pre_generated_world(src: CommandSource):
    info_list = storage.get_slots_info(allow_used=True)
    rt = list()
    rt.append(tr('msg.info_title', len(info_list), config.max_slots))
    for slot_dir, slot_info in info_list.items():
        rt.append(single_info(os.path.basename(slot_dir), slot_info.used))
    src.reply(RTextBase.join('\n', rt))


def info_slot(src: CommandSource, slot_name: str):
    def format_dir_size(size: int):
        if size < 2 ** 30:
            return f'{round(size / 2 ** 20, 2)} MB'
        else:
            return f'{round(size / 2 ** 30, 2)} GB'

    slot_info = get_slot(slot_name)
    rt = [
        single_info(slot_name, used=slot_info.used),
        tr('info.used', slot_info.used),
        tr('info.size', format_dir_size(storage.get_slot_size(slot_name))),
        tr('info.time', time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(slot_info.timestamp))),
        tr('info.comment', slot_info.comment)
    ]
    src.reply(RTextBase.join('\n', rt))


def confirm_current_work(src: CommandSource):
    if RunningSession.is_avail():
        src.reply(tr('error.no_session').set_color(RColor.red))
        return
    running_session = RunningSession.running_session
    if running_session.is_running:
        src.reply(tr('error.session_already_running').set_color(RColor.red))
        return
    try:
        running_session.is_running = True
        running_session.main()
    except Exception as exc:
        global_psi.logger.exception('Error occurred while running Pre-generator: ')
        running_session.on_error(exc)


def abort_current_work(src: CommandSource):
    if RunningSession.is_avail():
        src.reply(tr('error.no_session').set_color(RColor.red))
        return
    running_session = RunningSession.running_session
    if running_session.is_running:
        src.reply(tr('error.session_already_running').set_color(RColor.red))
        return
    RunningSession.clear()
    src.reply(tr('msg.aborted'))


def register_command():
    def permed_literal(*cmd):
        perm = 1
        for item in cmd:
            target_perm = config.get_prem(item)
            if target_perm > perm:
                perm = target_perm
        return Literal(cmd).requires(lambda src: src.has_permission(target_perm))

    def show_error_msg(src: CommandSource, exc: CommandError):
        if isinstance(exc, RequirementNotMet):
            src.reply(tr('error.perm', exc.get_reason()).set_color(RColor.red))
        elif isinstance(exc, SlotNotFound):
            src.reply(tr('error.slot_not_found', exc.slot_name).set_color(RColor.red).h(
                tr('hover.list')).c(RAction.run_command, f"{config.prefix[0]} list"))
        else:
            src.reply(tr('error.cmd').set_color(RColor.red).h(tr('hover.help')).c(RAction.run_command, config.prefix[0]))

    root_node = Literal(config.prefix).runs(lambda src: show_help(src)).on_child_error(CommandError, show_error_msg, handled=True)
    children_nodes = [
        permed_literal('gen', 'generate').runs(lambda src: pre_generate_worlds(src)).then(
            Integer('pregen_amount').runs(lambda src, ctx: pre_generate_worlds(src, ctx['pregen_amount'])).then(
                GreedyText('comment').runs(lambda src, ctx: pre_generate_worlds(src, ctx['pregen_amount'], ctx['comment']))
            )
        ),
        permed_literal('load').then(
            QuotableText('slot_name').runs(lambda src, ctx: load_pre_generated_world(src, ctx['slot_name']))
        ),
        permed_literal('next').runs(lambda src: load_pre_generated_world(src)),
        permed_literal('list').runs(lambda src: list_pre_generated_world(src)),
        permed_literal('info').then(
            QuotableText('slot_name').runs(lambda src, ctx: info_slot(src, ctx['slot_name']))
        ),
        permed_literal('confirm').runs(lambda src: confirm_current_work(src)),
        permed_literal('abort').runs(lambda src: abort_current_work(src)),
        permed_literal('reload').runs(lambda src: reload_self(src)).then(
            Literal('--clear').runs(lambda src: reload_self(src, throw_session=True))
        ),
        permed_literal('remove').then(
            QuotableText('slot_name').runs(lambda src, ctx: remove_pre_generated_world(src, ctx['slot_name']))
        ),
        permed_literal('autoremove').runs(lambda src: auto_remove_used_world(src))
    ]
    debug_nodes = [
        permed_literal('status').runs(lambda src: src.reply('Current session status: {} Running: {}'.format(
            RunningSession.is_avail(),
            RunningSession.running_session.is_running if not RunningSession.is_avail() else False)))
    ]

    for node in children_nodes:
        root_node.then(node)
    if DEBUG:
        for node in debug_nodes:
            root_node.then(node)
    global_psi.register_command(root_node)
