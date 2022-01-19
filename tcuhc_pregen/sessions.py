import os
import shutil
from threading import RLock
from typing import Optional
from parse import parse
from mcdreforged.api.all import *

from tcuhc_pregen.config import config
from tcuhc_pregen.storage import storage, SLOT_INFO_FILE
from tcuhc_pregen.utils import global_psi, tr, stop_and_wait, debug_log, cp, rm


class RunningSession:
    running_session: Optional['AbstractSession'] = None

    @classmethod
    def is_avail(cls):
        return cls.running_session is None

    @classmethod
    def clear(cls):
        if cls.is_avail():
            debug_log('Nothing to clear')
        else:
            debug_log('Session removed')
        cls.running_session = None


class AbstractSession:
    def __init__(self):
        self.__lock = RLock()
        self.is_running = False

    def main(self):
        raise NotImplementedError

    def on_info(self, info: Info):
        raise NotImplementedError

    def on_error(self, exc: Exception):
        raise NotImplementedError


class PreGenerationSession(AbstractSession):
    def __init__(self, required_amount: int, comment: str):
        super(PreGenerationSession, self).__init__()
        self.__num = required_amount
        self.__comment = comment
        self.__dimension_result = {dimension: False for dimension in config.wait_dimensions}
        self.__allow_info = False

    def main(self):
        global_psi.broadcast(tr('msg.start_pregen', config.countdown_time))
        stop_and_wait(countdown=config.countdown_time, stop_command=config.regen_command)
        global_psi.start()
        self.__allow_info = True

    def on_info(self, info: Info):
        if self.__allow_info:
            for item in config.keywords.generation_finished:
                parsed = parse(item, info.content)
                if parsed is not None and parsed.named.get('dimension') is not None:
                    self.__dimension_result[parsed['dimension']] = True
                    debug_log(f"Found world {parsed['dimension']} generation finished")
                    break

            if all(self.__dimension_result.values()):
                debug_log("All the world generation finished")
                self.__num -= 1
                global_psi.broadcast(tr('msg.finished_load', config.countdown_time))
                stop_and_wait(config.countdown_time, stop_command=config.regen_command)
                debug_log(f'Awaiting generation amount: {self.__num}')
                storage.backup(config.world_names, self.__comment)
                global_psi.start()
                self.__dimension_result = {dimension: False for dimension in config.wait_dimensions}
            if self.__num <= 0:
                debug_log('Pre-generation finished, exiting')
                RunningSession.clear()

    def on_error(self, exc: Exception):
        global_psi.start()
        global_psi.broadcast(tr('error.backup_failed', exc=str(exc)))
        RunningSession.clear()


class LoadSlotSession(AbstractSession):
    def __init__(self, name: str):
        super(LoadSlotSession, self).__init__()
        self.__slot_to_load = storage.slot_dir_path(name)
        self.backed_up = []
        self.moved = []
        self.temp_folder = os.path.join(config.server_path, config.restore_temp_folder)
        self.finished_backup = False
        if not os.path.isdir(self.__slot_to_load):
            raise FileNotFoundError('This slot is not found')

    def on_info(self, info: Info):
        pass

    def main(self):
        global_psi.broadcast(tr('msg.before_load', config.countdown_time))
        stop_and_wait(config.countdown_time)
        if not os.path.isdir(self.temp_folder):
            os.makedirs(self.temp_folder)
            debug_log('Generated temp folder')

        # back world files up
        for item in config.world_names:
            cp(os.path.join(config.server_path, item), os.path.join(self.temp_folder, item))

        # remove current world file
        self.finished_backup = True
        for item in config.world_names:
            rm(os.path.join(config.server_path, item))

        # copy file to server directory
        for item in os.listdir(self.__slot_to_load):
            if item != SLOT_INFO_FILE:
                cp(os.path.join(self.__slot_to_load, item), os.path.join(config.server_path, item))

        shutil.rmtree(self.temp_folder)

        current_info = storage.get_slots_info(allow_used=True).get(os.path.basename(self.__slot_to_load))
        debug_log(os.path.basename(self.__slot_to_load))
        current_info.used = True
        current_info.save(os.path.basename(self.__slot_to_load))
        global_psi.start()
        RunningSession.clear()

    def on_error(self, exc: Exception):
        RunningSession.clear()
        if self.finished_backup:
            for item in self.moved:
                rm(os.path.join(config.server_path, item))
            for item in self.backed_up:
                cp(os.path.join(self.temp_folder, item), os.path.join(config.server_path, item))
        if os.path.isdir(self.temp_folder):
            shutil.rmtree(self.temp_folder)
        global_psi.start()


class RemoveSlotSession(AbstractSession):
    def __init__(self, name: str):
        super(RemoveSlotSession, self).__init__()
        self.name = name

    def main(self):
        storage.remove_slot(self.name)
        global_psi.broadcast(tr('msg.removed', self.name))
        RunningSession.clear()

    def on_error(self, exc: Exception):
        RunningSession.clear()
        global_psi.broadcast(tr('error.occurred', str(exc)))

    def on_info(self, info: Info):
        pass


class AutoRemoveSlotSession(AbstractSession):
    def __init__(self):
        super(AutoRemoveSlotSession, self).__init__()

    def main(self):
        num = storage.auto_remove()
        global_psi.broadcast(tr('msg.auto_removed', num))
        RunningSession.clear()

    def on_error(self, exc: Exception):
        RunningSession.clear()
        global_psi.broadcast(tr('error.occurred', str(exc)))

    def on_info(self, info: Info):
        pass
