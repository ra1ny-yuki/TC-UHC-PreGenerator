import re
import time
import os
import shutil

from mcdreforged.api.all import *
from typing import Union

from tcuhc_pregen.config import config


global_psi = ServerInterface.get_instance().as_plugin_server_interface()
DEBUG = False


def cp(this_file: str, target_file: str, allow_not_found=True):
    if os.path.isfile(this_file):
        shutil.copy(this_file, target_file)
        debug_log(f'Copied file "{this_file}" to "{target_file}"')
    elif os.path.isdir(this_file):
        shutil.copytree(this_file, target_file)
        debug_log(f'Copied folder "{this_file}" to "{target_file}"')
    else:
        debug_log(f'File {this_file} not found')
        if not allow_not_found:
            raise FileNotFoundError(f'File not found: {this_file}')


def rm(this_file: str, allow_not_found=True):
    if os.path.isfile(this_file):
        os.remove(this_file)
        debug_log(f'Removed file "{this_file}"')
    elif os.path.isdir(this_file):
        shutil.rmtree(this_file)
        debug_log(f'Removed folder "{this_file}"')
    else:
        debug_log(f'4 File {this_file} not found')
        if not allow_not_found:
            raise FileNotFoundError(f'File not found: {this_file}')


def debug_log(text: str):
    global_psi.logger.debug(text, no_check=DEBUG)


def stop_and_wait(countdown: int = 5, stop_command: str = None):
    for num in range(0, countdown):
        global_psi.broadcast(tr('msg.countdown', countdown - num).set_color(RColor.red))
        time.sleep(1)
    if stop_command is None:
        global_psi.stop()
    else:
        global_psi.execute(stop_command)
    global_psi.wait_for_start()


def tr(translation_key: str, *args, **kwargs):
    key = translation_key if translation_key.startswith('pregen.') else f'pregen.{translation_key}'
    return global_psi.rtr(key, *args, **kwargs)


def htr(key: str, *args, **kwargs) -> Union[str, RTextBase]:
    help_message, help_msg_rtext = global_psi.tr(key, *args, **kwargs), RTextList()
    if not isinstance(help_message, str):
        global_psi.logger.error('Error translate text "{}"'.format(key))
        return key
    for line in help_message.splitlines():
        result = re.search(r'(?<=§7){}[\S ]*?(?=§)'.format(config.prefix[0]), line)
        if result is not None:
            cmd = result.group() + ' '
            help_msg_rtext.append(RText(line).c(RAction.suggest_command, cmd).h(tr('hover.suggest', cmd)))
        else:
            help_msg_rtext.append(line)
        if line != help_message.splitlines()[-1]:
            help_msg_rtext.append('\n')
    return help_msg_rtext
