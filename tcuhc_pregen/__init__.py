from mcdreforged.api.all import *
from tcuhc_pregen.config import config
from tcuhc_pregen.utils import debug_log, tr
from tcuhc_pregen.sessions import RunningSession
from tcuhc_pregen.core import register_command


def on_info(server: PluginServerInterface, info: Info):
    if not RunningSession.is_avail() and RunningSession.running_session.is_running:
        try:
            RunningSession.running_session.on_info(info)
        except Exception as exc:
            RunningSession.running_session.on_error(exc)
            server.logger.exception('Error occurred while running pre-generator:')


def on_load(server: PluginServerInterface, prev_module):
    if prev_module is not None:
        RunningSession.running_session = prev_module.RunningSession.running_session
    for prefix in config.prefix:
        server.register_help_message(prefix, tr('help.mcdr'))
    register_command()
